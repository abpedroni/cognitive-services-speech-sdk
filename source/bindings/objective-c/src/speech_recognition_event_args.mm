//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#import "speechapi_private.h"

@implementation SpeechRecognitionEventArgs

- (instancetype)init:(const SpeechImpl::SpeechRecognitionEventArgs&)e
{
    self = [super init:e];
    _result = [[SpeechRecognitionResult alloc] init:e.GetResult()];
    return self;
}

@end

@implementation SpeechRecognitionCanceledEventArgs

- (instancetype)init:(const SpeechImpl::SpeechRecognitionCanceledEventArgs&)e
{
    self = [super init:e];
    auto cancellationDetails = e.GetCancellationDetails();
    _reason = [Util fromCancellationReasonImpl:cancellationDetails->Reason];
    _errorDetails = [NSString stringWithString:cancellationDetails->ErrorDetails];
    
    return self;
}

@end
