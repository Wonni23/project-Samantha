import 'dart:io';
import 'package:flutter/services.dart';
import 'package:frontend/core/utils/logger.dart';

/// 앱 내부에서 로컬 에셋을 HTTP로 서빙하는 초경량 서버
class LocalAssetServer {
  static HttpServer? _server;
  static const int port = 8080;

  static Future<void> start() async {
    if (_server != null) return;

    try {
      _server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
      logger.i('🌐 Local Asset Server started on http://localhost:$port');

      _server!.listen((HttpRequest request) async {
        try {
          // 요청 경로에서 에셋 경로 추출
          String path = request.uri.path;
          if (path == '/') path = '/index.html';
          
          // assets/www 폴더 내의 파일로 매핑
          final assetPath = 'assets/www${path}';
          
          try {
            final data = await rootBundle.load(assetPath);
            final buffer = data.buffer.asUint8List();

            // MIME 타입 설정
            if (path.endsWith('.html')) request.response.headers.contentType = ContentType.html;
            else if (path.endsWith('.js')) request.response.headers.contentType = ContentType('application', 'javascript');
            else if (path.endsWith('.json')) request.response.headers.contentType = ContentType.json;
            else if (path.endsWith('.png')) request.response.headers.contentType = ContentType('image', 'png');
            else if (path.endsWith('.css')) request.response.headers.contentType = ContentType('text', 'css');

            request.response.add(buffer);
          } catch (e) {
            request.response.statusCode = HttpStatus.notFound;
            logger.w('🌐 Local Server 404: $assetPath');
          }
        } catch (e) {
          request.response.statusCode = HttpStatus.internalServerError;
          logger.e('🌐 Local Server Error', error: e);
        } finally {
          await request.response.close();
        }
      });
    } catch (e) {
      logger.e('🌐 Failed to start Local Asset Server', error: e);
    }
  }

  static void stop() {
    _server?.close();
    _server = null;
  }
}
