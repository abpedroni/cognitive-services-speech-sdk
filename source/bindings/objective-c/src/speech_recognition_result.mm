//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#import "speech_recognition_result_private.h"
#import "common_private.h"

@implementation SPXSpeechRecognitionResult
{
    std::shared_ptr<SpeechImpl::SpeechRecognitionResult> resultImpl;
}

- (instancetype)init :(std::shared_ptr<SpeechImpl::SpeechRecognitionResult>)resultHandle
{
    self = [super init :resultHandle];
    resultImpl = resultHandle;
    return self;
}

@end
