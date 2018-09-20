//
// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
//

#import <Foundation/Foundation.h>
#import <string>

@interface NSString (STL)

- (std::string)string;
+ (instancetype)stringWithString:(const std::string&)str;

@end