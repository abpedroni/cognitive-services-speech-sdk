# Copyright (c) Microsoft. All rights reserved.
# See https://aka.ms/csspeech/license201809 for the full license information.

import functools
import os
import requests
import time

import azure.cognitiveservices.speech as msspeech

from .utils import _TestCallback

from .test_events import _check_events

from .tts_utils import (_PushAudioOutputStreamTestCallback,
                    _do_something_with_audio_in_push_stream,
                    _do_something_with_audio_in_pull_stream,
                    _do_something_with_audio_in_pull_stream_in_background,
                    _do_something_with_audio_in_vector,
                    _do_something_with_audio_in_data_stream,
                    _do_something_with_audio_in_data_stream_in_background,
                    _do_something_with_audio_in_result_in_background,
                    _synthesis_started_counter,
                    _synthesis_completed_counter,
                    _synthesis_canceled_counter,
                    _synthesis_started_event_check,
                    _synthesizing_event_check,
                    _synthesis_word_boundary_event_check_plain_text,
                    _synthesis_word_boundary_event_check_ssml)


def test_speech_synthesizer_defaults(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    synthesizer = msspeech.SpeechSynthesizer(config)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has now completed rendering to default speakers
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has now completed rendering to default speakers


def test_speech_synthesizer_explicitly_use_default_speakers(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    device_config = msspeech.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = msspeech.SpeechSynthesizer(config, device_config)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has now completed rendering to default speakers
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has now completed rendering to default speakers


def test_speech_synthesizer_pick_language(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    config.speech_synthesis_language = "en-GB"

    synthesizer = msspeech.SpeechSynthesizer(config)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has now completed rendering to default speakers
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has now completed rendering to default speakers


def test_speech_synthesizer_pick_voice(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    config.speech_synthesis_voice_name = "Microsoft Server Speech Text to Speech Voice (en-GB, HazelRUS)"

    synthesizer = msspeech.SpeechSynthesizer(config)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has now completed rendering to default speakers
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has now completed rendering to default speakers


def test_speech_synthesizer_synthesizer_output_to_file(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    file_config = msspeech.audio.AudioOutputConfig(filename="wavefile.wav")

    synthesizer = msspeech.SpeechSynthesizer(config, file_config)
    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{wavefile.wav}}}" now contains synthesized audio for "{{{text1}}}""
    result_reason1 = result1.reason
    result1 = None
    synthesizer = None
    # "{{{wavefile.wav}}}" is now closed

    wave_size_1 = os.path.getsize("wavefile.wav")
    if result_reason1 != msspeech.ResultReason.Canceled:
        assert wave_size_1 > 46 # 46 is the minimum size of a wav file

    synthesizer = msspeech.SpeechSynthesizer(config, file_config)
    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{wavefile.wav}}}" now contains synthesized audio for "{{{text1}}}""
    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{wavefile.wav}}}" now contains synthesized audio for both "{{{text1}}}"" and "{{{text2}}}"
    result_reason21 = result1.reason
    result_reason22 = result2.reason
    result1 = None
    result2 = None
    synthesizer = None
    # "{{{wavefile.wav}}}" is now closed

    wave_size_2 = os.path.getsize("wavefile.wav")
    if result_reason1 != msspeech.ResultReason.Canceled:
        if result_reason21 != msspeech.ResultReason.Canceled:
            if result_reason22 != msspeech.ResultReason.Canceled:
                assert wave_size_2 > wave_size_1


def test_speech_synthesizer_synthesizer_output_to_mp3_file(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    file_config = msspeech.audio.AudioOutputConfig(filename="audiofile.wav")

    synthesizer = msspeech.SpeechSynthesizer(config, file_config)
    result = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{audiofile.wav}}}" now contains synthesized audio for "{{{text1}}}""
    result_reason1 = result.reason
    result = None
    synthesizer = None
    # "{{{audiofile.wav}}}" is now closed

    wave_file_size = os.path.getsize("audiofile.wav")
    if result_reason1 != msspeech.ResultReason.Canceled:
        assert wave_file_size > 46 # 46 is the minimum size of a wav file

    config.set_speech_synthesis_output_format(msspeech.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
    assert "audio-16khz-32kbitrate-mono-mp3" == config.speech_synthesis_output_format_string

    file_config = msspeech.audio.AudioOutputConfig(filename="audiofile.mp3")
    synthesizer = msspeech.SpeechSynthesizer(config, file_config)
    result = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{audiofile.mp3}}}" now contains synthesized audio for "{{{text1}}}""
    result_reason2 = result.reason
    result = None
    synthesizer = None
    # "{{{audiofile.mp3}}}" is now closed

    mp3_file_size = os.path.getsize("audiofile.mp3")
    if result_reason2 != msspeech.ResultReason.Canceled:
        assert mp3_file_size > 0

    if result_reason1 != msspeech.ResultReason.Canceled:
        if result_reason2 != msspeech.ResultReason.Canceled:
            assert mp3_file_size < wave_file_size


def test_speech_synthesizer_synthesizer_output_to_push_stream(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    stream_callback = _PushAudioOutputStreamTestCallback()
    push_stream = msspeech.audio.PushAudioOutputStream(stream_callback)
    stream_config = msspeech.audio.AudioOutputConfig(stream=push_stream)

    synthesizer = msspeech.SpeechSynthesizer(config, stream_config)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering to pullstream
    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering to pullstream

    result1_canceled = result1.reason == msspeech.ResultReason.Canceled
    result2_canceled = result2.reason == msspeech.ResultReason.Canceled
    canceled = result1_canceled and result2_canceled

    result1 = None
    result2 = None
    synthesizer = None

    _do_something_with_audio_in_push_stream(stream_callback, canceled)


def test_speech_synthesizer_synthesizer_output_to_pull_stream_use_after_synthesis_completed(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    pull_stream = msspeech.audio.PullAudioOutputStream()
    stream_config = msspeech.audio.AudioOutputConfig(stream=pull_stream)

    synthesizer = msspeech.SpeechSynthesizer(config, stream_config)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering to pullstream
    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering to pullstream

    result1_canceled = result1.reason == msspeech.ResultReason.Canceled
    result2_canceled = result2.reason == msspeech.ResultReason.Canceled
    canceled = [result1_canceled and result2_canceled]

    result1 = None
    result2 = None
    synthesizer = None

    _do_something_with_audio_in_pull_stream(pull_stream, canceled)


def test_speech_synthesizer_synthesizer_output_to_pull_stream_start_using_before_done_synthesizing(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)

    pull_stream = msspeech.audio.PullAudioOutputStream()

    canceled = [False]
    future = _do_something_with_audio_in_pull_stream_in_background(pull_stream, canceled)

    stream_config = msspeech.audio.AudioOutputConfig(stream=pull_stream)
    synthesizer = msspeech.SpeechSynthesizer(config, stream_config)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering to pullstream
    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering to pullstream

    result1_canceled = result1.reason == msspeech.ResultReason.Canceled
    result2_canceled = result2.reason == msspeech.ResultReason.Canceled
    canceled[0] = result1_canceled and result2_canceled

    result1 = None
    result2 = None
    synthesizer = None

    future.result()


def test_speech_synthesizer_speak_out_in_results(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering, and available in result1
    assert len(result1.result_id) > 0
    if result1.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result1.reason
        audio_data1 = result1.audio_data  # of type bytes
        _do_something_with_audio_in_vector(audio_data1)

    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering, and available in result2
    assert len(result2.result_id) > 0
    if result2.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result2.reason
        audio_data2 = result2.audio_data  # of type bytes
        _do_something_with_audio_in_vector(audio_data2)


def test_speech_synthesizer_speak_output_in_chunks_in_event_synthesizing(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    synthesizer = msspeech.SpeechSynthesizer(config, None)
    # None(null) indicates to do nothing with synthesizer audio by default

    synthesizing_callback = _TestCallback(
        "In synthesizing callback: {evt}", event_checks=_synthesizing_event_check)
    synthesizer.synthesizing.connect(synthesizing_callback)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering

    callbacks = {'synthesizing_callback': synthesizing_callback}
    _check_events(callbacks)


def test_speech_synthesizer_speak_output_in_streams(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
     # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering, and available in result1
    if result1.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result1.reason
        assert len(result1.audio_data) > 0

    stream1 = msspeech.AudioDataStream(result1)  # of type AudioDataStream, does not block
    _do_something_with_audio_in_data_stream(stream1, True)

    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering, and available in result2
    if result2.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result2.reason
        assert len(result2.audio_data) > 0

    stream2 = msspeech.AudioDataStream(result2)  # of type AudioDataStream, does not block
    _do_something_with_audio_in_data_stream(stream2, True)


def test_speech_synthesizer_speak_output_in_streams_before_done_from_event_synthesis_started(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    synthesis_started_callback = _TestCallback(
        "In synthesis started callback: {evt}", event_checks=_synthesis_started_event_check)
    synthesizer.synthesis_started.connect(synthesis_started_callback)

    synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering
    synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering

    future3 = synthesizer.speak_text_async("{{{text3}}}")
    # "{{{text3}}}" synthesis might have started
    result3 = future3.get()
    # "{{{text3}}}" synthesis has completed

    callbacks = {'synthesis_started_callback': synthesis_started_callback}
    _check_events(callbacks)


def test_speech_synthesizer_speak_output_in_streams_before_done_from_method_start_speaking_text_async(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    result1 = synthesizer.start_speaking_text_async("{{{text1}}}").get()
    # "{{{text1}}}" synthesis has started, likely not finished
    assert msspeech.ResultReason.SynthesizingAudioStarted == result1.reason
    assert 0 == len(result1.audio_data)

    stream1 = msspeech.AudioDataStream(result1)  # of type AudioDataStream, does not block
    future1 = _do_something_with_audio_in_data_stream_in_background(stream1, False)
    # does not block, just spins a thread up

    result2 = synthesizer.start_speaking_text_async("{{{text2}}}").get()
    # "{{{text2}}}" synthesis has started, likely not finished
    assert msspeech.ResultReason.SynthesizingAudioStarted == result2.reason
    assert 0 == len(result2.audio_data)

    stream2 = msspeech.AudioDataStream(result2)  # of type AudioDataStream, does not block
    future2 = _do_something_with_audio_in_data_stream_in_background(stream2, False)
    # does not block, just spins a thread up

    future1.result()
    future2.result()


def test_speech_synthesizer_speak_output_in_streams_before_done_queued(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    counter = {'_started_speak_requests': 0, '_done_speak_requests': 0}

    synthesis_started_counter_callback = _TestCallback("In synthesis started counter: {evt}",
        event_checks=functools.partial(_synthesis_started_counter, counter=counter))
    synthesizer.synthesis_started.connect(synthesis_started_counter_callback)

    synthesis_completed_counter_callback = _TestCallback("In synthesis completed counter: {evt}",
        event_checks=functools.partial(_synthesis_completed_counter, counter=counter))
    synthesizer.synthesis_completed.connect(synthesis_completed_counter_callback)

    synthesis_canceled_counter_callback = _TestCallback("In synthesis canceled counter: {evt}",
        event_checks=functools.partial(_synthesis_canceled_counter, counter=counter))
    synthesizer.synthesis_canceled.connect(synthesis_canceled_counter_callback)

    future_result1 = synthesizer.start_speaking_text_async("{{{text1}}}")
    # "{{{text1}}}" synthesis might have started, likely not finished
    future_result2 = synthesizer.start_speaking_text_async("{{{text2}}}")
    # "{{{text2}}}" synthesis might have started (very unlikely)

    future1 = _do_something_with_audio_in_result_in_background(future_result1, False)
    # does not block, just spins a thread up
    future2 = _do_something_with_audio_in_result_in_background(future_result2, False)
    # does not block, just spins a thread up

    try:
        future1.result()
        future2.result()
    except Exception as ex:
        while counter['_done_speak_requests'] < 2:
            time.sleep(0.1)
        synthesizer = None
        raise ex

    while counter['_done_speak_requests'] < 2:
        time.sleep(0.1)

    callbacks = {'synthesis_started_counter_callback': synthesis_started_counter_callback,
        'synthesis_completed_counter_callback': synthesis_completed_counter_callback,
        'synthesis_canceled_counter_callback': synthesis_canceled_counter_callback}
    _check_events(callbacks)


def test_speech_synthesizer_speak_output_in_streams_with_all_data_get_on_synthesis_started_result(
    subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    counter = {'_started_speak_requests': 0, '_done_speak_requests': 0}

    synthesis_started_counter_callback = _TestCallback("In synthesis started counter: {evt}",
        event_checks=functools.partial(_synthesis_started_counter, counter=counter))
    synthesizer.synthesis_started.connect(synthesis_started_counter_callback)

    synthesis_completed_counter_callback = _TestCallback("In synthesis completed counter: {evt}",
        event_checks=functools.partial(_synthesis_completed_counter, counter=counter))
    synthesizer.synthesis_completed.connect(synthesis_completed_counter_callback)

    synthesis_canceled_counter_callback = _TestCallback("In synthesis canceled counter: {evt}",
        event_checks=functools.partial(_synthesis_canceled_counter, counter=counter))
    synthesizer.synthesis_canceled.connect(synthesis_canceled_counter_callback)

    result = synthesizer.start_speaking_text_async("{{{text1}}}").get()
    # "{{{text1}}}" synthesis has started, likely not finished
    assert msspeech.ResultReason.SynthesizingAudioStarted == result.reason
    assert 0 == len(result.audio_data)

    while counter['_done_speak_requests'] == 0:
        time.sleep(0.1)

    stream = msspeech.AudioDataStream(result)
    _do_something_with_audio_in_data_stream(stream, True)

    callbacks = {'synthesis_started_counter_callback': synthesis_started_counter_callback,
        'synthesis_completed_counter_callback': synthesis_completed_counter_callback,
        'synthesis_canceled_counter_callback': synthesis_canceled_counter_callback}
    _check_events(callbacks)


def test_speech_synthesizer_check_word_boundary_events(subscription, speech_region):
    config = msspeech.SpeechConfig(subscription=subscription, region=speech_region)
    config.speech_synthesis_voice_name = "Microsoft Server Speech Text to Speech Voice (zh-CN, HuihuiRUS)"
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)

    plain_text = "您好，我是来自Microsoft的中文声音。"
    ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xmlns:emo='http://www.w3.org/2009/10/emotionml' xml:lang='zh-CN'><voice name='Microsoft Server Speech Text to Speech Voice (zh-CN, HuihuiRUS)'>您好，<break time='50ms'/>我是来自Microsoft的中文声音。</voice></speak>"

    expected_audio_offsets = [500000, 7443750, 9175620, 10585000, 15096880, 22924380, 25213120, 28760000]
    expected_text_offsets = [0, 3, 4, 5, 7, 16, 17, 19]
    expected_ssml_offsets = [251, 274, 275, 276, 278, 287, 288, 290]
    expected_word_lengths = [2, 1, 1, 2, 9, 1, 2, 2]

    counter = {'_word_boundary_events': 0}

    synthesis_word_boundary_check_plain_text_callback = _TestCallback(
        "In synthesis word boundary check plain text callback: {evt}",
        event_checks=functools.partial(_synthesis_word_boundary_event_check_plain_text, counter=counter,
        expected_audio_offsets=expected_audio_offsets,
        expected_text_offsets = expected_text_offsets,
        expected_word_lengths=expected_word_lengths))
    synthesizer.synthesis_word_boundary.connect(synthesis_word_boundary_check_plain_text_callback)
    result = synthesizer.speak_text_async(plain_text).get()

    assert 8 == counter['_word_boundary_events']

    synthesizer.synthesis_word_boundary.disconnect_all()
    counter['_word_boundary_events'] = 0

    synthesis_word_boundary_check_ssml_callback = _TestCallback(
        "In synthesis word boundary check ssml callback: {evt}",
        event_checks=functools.partial(_synthesis_word_boundary_event_check_ssml, counter=counter,
        expected_audio_offsets=expected_audio_offsets,
        expected_ssml_offsets = expected_ssml_offsets,
        expected_word_lengths=expected_word_lengths))
    synthesizer.synthesis_word_boundary.connect(synthesis_word_boundary_check_ssml_callback)
    result = synthesizer.speak_ssml_async(ssml).get()

    assert 8 == counter['_word_boundary_events']

    callbacks = {'synthesis_word_boundary_check_plain_text_callback':
                 synthesis_word_boundary_check_plain_text_callback,
                 'synthesis_word_boundary_check_ssml_callback':
                 synthesis_word_boundary_check_ssml_callback}
    _check_events(callbacks)


def get_token(subscription, region):
    fetch_token_url = "https://{}.api.cognitive.microsoft.com/sts/v1.0/issueToken".format(region)
    headers = {
        'Ocp-Apim-Subscription-Key': subscription
    }
    response = requests.post(fetch_token_url, headers=headers)
    return str(response.text)


def test_speech_synthesizer_speak_out_with_authorization_token(subscription, speech_region):
    config = msspeech.SpeechConfig(auth_token="InvalidToken", region=speech_region)
    # None(null) indicates to do nothing with synthesizer audio by default
    synthesizer = msspeech.SpeechSynthesizer(config, None)
    assert "InvalidToken" == synthesizer.authorization_token

    # Set token to the synthesizer
    synthesizer.authorization_token = get_token(subscription, speech_region)

    result1 = synthesizer.speak_text_async("{{{text1}}}").get()
    # "{{{text1}}}" has completed rendering, and available in result1
    assert len(result1.result_id) > 0
    if result1.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result1.reason
        audio_data1 = result1.audio_data  # of type bytes
        _do_something_with_audio_in_vector(audio_data1)

    result2 = synthesizer.speak_text_async("{{{text2}}}").get()
    # "{{{text2}}}" has completed rendering, and available in result2
    assert len(result2.result_id) > 0
    if result2.reason != msspeech.ResultReason.Canceled:
        assert msspeech.ResultReason.SynthesizingAudioCompleted == result2.reason
        audio_data2 = result2.audio_data  # of type bytes
        _do_something_with_audio_in_vector(audio_data2)
