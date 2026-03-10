import 'dart:io';
import 'dart:typed_data';
import 'package:path_provider/path_provider.dart';

class PlatformUtilsImpl {
  static Future<String> getPlayableUrl(Uint8List audioData) async {
    final tempDir = await getTemporaryDirectory();
    final filePath =
        '${tempDir.path}/ai_response_${DateTime.now().millisecondsSinceEpoch}.mp3';
    final file = File(filePath);
    await file.writeAsBytes(audioData);
    return filePath;
  }

  static void revokeUrl(String url) {
    // 로컬 파일의 경우 필요에 따라 삭제 로직을 넣을 수 있지만,
    // 여기서는 웹 Blob URL 해제와 시그니처를 맞추기 위해 비워둡니다.
  }

  static Future<Uint8List?> fetchBytes(String url) async {
    final file = File(url);
    if (await file.exists()) {
      return await file.readAsBytes();
    }
    return null;
  }
}
