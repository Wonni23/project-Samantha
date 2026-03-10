import 'dart:typed_data';

/// 플랫폼별 구현을 위한 기본 클래스
class PlatformUtilsImpl {
  static Future<String> getPlayableUrl(Uint8List audioData) async {
    throw UnsupportedError('Cannot create playable URL on this platform');
  }

  static void revokeUrl(String url) {}

  static Future<Uint8List?> fetchBytes(String url) async {
    throw UnsupportedError('Cannot fetch bytes on this platform');
  }
}
