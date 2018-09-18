//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#import "translation_synthesis_result_private.h"

#import "common_private.h"

@implementation TranslationSynthesisResult
{
    std::shared_ptr<TranslationImpl::TranslationSynthesisResult> resultImpl;
}

- (instancetype)init :(std::shared_ptr<TranslationImpl::TranslationSynthesisResult>)resultHandle
{
    self = [super init];
    resultImpl = resultHandle;

    _audio = [NSData dataWithBytes:resultImpl->Audio.data() length:resultImpl->Audio.size()*sizeof(resultImpl->Audio[0])];

    return self;
}

@end