//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#include "stdafx.h"
#include "audio_buffer.h"

namespace Microsoft {
namespace CognitiveServices {
namespace Speech {
namespace Impl {

    PcmAudioBuffer::PcmAudioBuffer(const WAVEFORMATEX& header)
        : m_header{ header },
          m_totalSizeInBytes{ 0 },
          m_currentChunk{ 0 },
          m_bufferStartOffsetInBytesTurnRelative{ 0 },
          m_bufferStartOffsetInBytesAbsolute{ 0 },
          m_bytesPerSample{ header.wBitsPerSample / 8u },
          m_samplesPerMillisecond{ header.nSamplesPerSec / MillisecondsInSecond }
    {
        // Make sure milliseconds are precisely represent samples.
        if (m_header.nSamplesPerSec % MillisecondsInSecond != 0)
        {
            throw std::runtime_error("Sample rate '" + std::to_string(m_header.nSamplesPerSec) + "' is not supported. " +
                std::string("There should be an integer number of samples in a millisecond. Please resample."));
        }

        if (m_header.wBitsPerSample % 8 != 0)
        {
            throw std::runtime_error("Bits per sample '" + std::to_string(m_header.wBitsPerSample) + "' is not supported. It should be dividable by 8.");
        }
    }

    void PcmAudioBuffer::Add(const std::shared_ptr<uint8_t>& data, uint64_t dataSize)
    {
        std::unique_lock<std::mutex> guard(m_lock);
        m_audioBuffers.push_back(std::make_shared<DataChunk>(data, dataSize));
        m_totalSizeInBytes += dataSize;
    }

    DataChunkPtr PcmAudioBuffer::GetNext()
    {
        std::unique_lock<std::mutex> guard(m_lock);
        return GetNextUnlocked();
    }

    void PcmAudioBuffer::NewTurn()
    {
        std::unique_lock<std::mutex> guard(m_lock);
        m_bufferStartOffsetInBytesTurnRelative = 0;
        m_currentChunk = 0;
    }

    void PcmAudioBuffer::DiscardBytes(uint64_t bytes)
    {
        std::unique_lock<std::mutex> guard(m_lock);
        DiscardBytesUnlocked(bytes);
    }

    // In case when we need to have a shared pointer A into a buffer that already
    // managed by some shared pointer B, we define a custom deleter that captures pointer B
    // and resets in when ref counter of pointer A gets to 0.
    struct PtrHolder
    {
        // Have to be mutable in order to reset it in the custom deleter.
        mutable std::shared_ptr<uint8_t> data;
    };

    void PcmAudioBuffer::DiscardBytesUnlocked(uint64_t bytes)
    {
        uint64_t chunkBytes = 0;
        while (!m_audioBuffers.empty() && bytes &&
               (chunkBytes = m_audioBuffers.front()->size) <= bytes)
        {
            bytes -= chunkBytes;
            m_audioBuffers.pop_front();
            m_currentChunk--;
            SPX_THROW_HR_IF(SPXERR_RUNTIME_ERROR, m_totalSizeInBytes < chunkBytes);
            m_totalSizeInBytes -= chunkBytes;
            m_bufferStartOffsetInBytesTurnRelative += chunkBytes;
            m_bufferStartOffsetInBytesAbsolute += chunkBytes;
        }

        if (m_audioBuffers.empty())
        {
            if (m_totalSizeInBytes != 0)
            {
                SPX_TRACE_ERROR("%s: Invalid state of the audio buffer, no chunks but totalSize %d", __FUNCTION__, (int)m_totalSizeInBytes);
                SPX_THROW_HR(SPXERR_RUNTIME_ERROR);
            }

            if (bytes > 0)
            {
                SPX_TRACE_WARNING("%s: Discarding more data than what is available in the buffer %d", __FUNCTION__, (int)bytes);
            }

            m_currentChunk = 0;
        }
        else if (bytes > 0)
        {
            m_audioBuffers.front()->size -= bytes;
            m_bufferStartOffsetInBytesTurnRelative += bytes;
            m_bufferStartOffsetInBytesAbsolute += bytes;
            auto holder = PtrHolder{ m_audioBuffers.front()->data };
            m_audioBuffers.front()->data = std::shared_ptr<uint8_t>(holder.data.get() + bytes, [holder](void *) { holder.data.reset(); });
            SPX_THROW_HR_IF(SPXERR_RUNTIME_ERROR, m_totalSizeInBytes < bytes);
            m_totalSizeInBytes -= bytes;
        }
    }

    void PcmAudioBuffer::DiscardTill(uint64_t offsetInTicks)
    {
        std::unique_lock<std::mutex> guard(m_lock);
        DiscardTillUnlocked(offsetInTicks);
    }

    uint64_t PcmAudioBuffer::DurationToBytes(uint64_t durationInTicks) const
    {
        return m_header.nChannels * m_bytesPerSample * m_samplesPerMillisecond * (durationInTicks / TicksInMillisecond);
    }

    uint64_t PcmAudioBuffer::BytesToDurationInTicks(uint64_t bytes) const
    {
        return (bytes * TicksInMillisecond) / (m_header.nChannels * m_bytesPerSample * m_samplesPerMillisecond);
    }

    uint64_t PcmAudioBuffer::ToAbsolute(uint64_t offsetInTicksTurnRelative) const
    {
        int64_t bytes = DurationToBytes(offsetInTicksTurnRelative) - m_bufferStartOffsetInBytesTurnRelative;
        return BytesToDurationInTicks(m_bufferStartOffsetInBytesAbsolute + bytes);
    }

    uint64_t PcmAudioBuffer::StashedSizeInBytes() const
    {
        std::unique_lock<std::mutex> guard(m_lock);
        uint64_t size = 0;
        for (size_t i = m_currentChunk; i < m_audioBuffers.size(); ++i)
        {
            size += m_audioBuffers[i]->size;
        }
        return size;
    }

    void PcmAudioBuffer::Drop()
    {
        std::unique_lock<std::mutex> guard(m_lock);

        // Discarding unconfirmed bytes that we have already sent to the service.
        uint64_t unconfirmedBytes = 0;
        for (size_t i = 0; i < m_currentChunk; ++i)
        {
            unconfirmedBytes += m_audioBuffers[i]->size;
        }
        DiscardBytesUnlocked(unconfirmedBytes);

        // Discarding chunks that we have not yet sent to the service.
        DataChunkPtr chunk;
        while ((chunk = GetNextUnlocked()) != nullptr)
        {
            DiscardBytesUnlocked(chunk->size);
        }
    }

    void PcmAudioBuffer::CopyNonAcknowledgedDataTo(AudioBufferPtr buffer) const
    {
        if (buffer.get() == this)
        {
            return;
        }

        std::unique_lock<std::mutex> guard(m_lock);
        for (const auto& c : this->m_audioBuffers)
            buffer->Add(c->data, c->size);
    }

    DataChunkPtr PcmAudioBuffer::GetNextUnlocked()
    {
        if (m_currentChunk >= m_audioBuffers.size())
        {
            // No data available.
            return nullptr;
        }

        DataChunkPtr result = m_audioBuffers[m_currentChunk];
        m_currentChunk++;
        return result;
    }

    void PcmAudioBuffer::DiscardTillUnlocked(uint64_t offsetInTicks)
    {
        int64_t bytes = DurationToBytes(offsetInTicks) - m_bufferStartOffsetInBytesTurnRelative;
        if (bytes < 0)
        {
            SPX_TRACE_WARNING("%s: Offset is not monothonically increasing. Current turn offset in bytes %d, discardging bytes", __FUNCTION__,
                (int)m_bufferStartOffsetInBytesTurnRelative,
                (int)bytes);
            return;
        }
        DiscardBytesUnlocked(bytes);
    }

}}}}