import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

/// 앱 전역에서 사용할 로거 인스턴스
/// 
/// [Development 모드]
/// - 모든 레벨의 로그를 출력합니다.
/// - 예쁜 포맷으로 출력됩니다.
/// 
/// [Release 모드]
/// - 로그 출력을 최소화하거나 비활성화합니다.
final logger = Logger(
  printer: PrettyPrinter(
    methodCount: 0, // 메서드 스택 표시는 0으로 설정하여 깔끔하게 유지
    errorMethodCount: 8, // 에러 발생 시에는 충분한 스택 표시
    lineLength: 80, // 한 줄 길이
    colors: true, // 색상 적용
    printEmojis: true, // 이모지 표시
    dateTimeFormat: DateTimeFormat.onlyTimeAndSinceStart, // 시간 표시 형식
  ),
  // 릴리스 모드에서는 로그를 출력하지 않도록 설정
  level: kReleaseMode ? Level.off : Level.debug,
);
