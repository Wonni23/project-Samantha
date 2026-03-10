import 'dart:typed_data';

// Conditional export
export 'platform_utils_stub.dart'
    if (dart.library.js_interop) 'platform_utils_web.dart'
    if (dart.library.io) 'platform_utils_io.dart';

/// 플랫폼별 파일 저장 및 URL 생성을 위한 유틸리티
abstract class PlatformUtils {
  /// 오디오 데이터를 재생 가능한 URL 또는 파일 경로로 변환합니다.
  static Future<String> getPlayableUrl(Uint8List audioData) {
    throw UnsupportedError(
      'Cannot create playable URL without platform implementation',
    );
  }

  /// 사용이 끝난 URL(예: 웹의 Blob URL)을 해제합니다.
  static void revokeUrl(String url) {}

  /// URL 또는 파일 경로로부터 바이트 데이터를 가져옵니다.
  static Future<Uint8List?> fetchBytes(String url) {
    throw UnsupportedError(
      'Cannot fetch bytes without platform implementation',
    );
  }
}
