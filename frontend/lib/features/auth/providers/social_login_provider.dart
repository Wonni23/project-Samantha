import 'package:flutter/material.dart';

// 1. 소셜 로그인 종류를 나타내는 enum 정의
enum SocialLoginProvider { google, kakao, naver }

// 2. 각 enum 값에 따른 속성을 반환하는 extension 정의
extension SocialLoginProviderExtension on SocialLoginProvider {
  String get text {
    switch (this) {
      case SocialLoginProvider.google:
        return 'Google로 로그인';
      case SocialLoginProvider.kakao:
        return '카카오로 로그인';
      case SocialLoginProvider.naver:
        return '네이버로 로그인';
    }
  }

  String get logoAsset {
    switch (this) {
      case SocialLoginProvider.google:
        return 'assets/logos/google_logo.svg';
      case SocialLoginProvider.kakao:
        return 'assets/logos/kakao_logo.svg';
      case SocialLoginProvider.naver:
        return 'assets/logos/naver_logo.svg';
    }
  }

  Color get backgroundColor {
    switch (this) {
      case SocialLoginProvider.google:
        return Colors.white;
      case SocialLoginProvider.kakao:
        return const Color(0xFFFEE500);
      case SocialLoginProvider.naver:
        return const Color(0xFF03C75A);
    }
  }

  Color get textColor {
    switch (this) {
      case SocialLoginProvider.google:
        return const Color(0xFF1F1F1F);
      case SocialLoginProvider.kakao:
        return Colors.black;
      case SocialLoginProvider.naver:
        return Colors.white;
    }
  }
}
