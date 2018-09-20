//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#import "SPXRecognitionResult.h"
#import "common_private.h"

@interface SPXRecognitionResult (Private)

- (instancetype)init:(std::shared_ptr<SpeechImpl::RecognitionResult>)resultHandle;

- (instancetype)initWithError:(NSString *)message;

- (std::shared_ptr<SpeechImpl::RecognitionResult>)getHandle;

@end

@interface SPXCancellationDetails (Private)

- (instancetype)initWithImpl:(std::shared_ptr<SpeechImpl::CancellationDetails>)handle;

@end

@interface SPXNoMatchDetails (Private)

- (instancetype)initWithImpl:(std::shared_ptr<SpeechImpl::NoMatchDetails>)handle;

@end
