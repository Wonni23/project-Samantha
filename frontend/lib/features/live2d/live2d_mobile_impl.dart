import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'package:frontend/core/utils/logger.dart';
import 'live2d_controller.dart';

class Live2DControllerImpl implements Live2DController {
  late final WebViewController _webController;
  final String _modelPath;

  Live2DControllerImpl(String viewId, String canvasId, this._modelPath) {
    _webController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFEFEBE0))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            logger.i('🎭 [Mobile] WebView load finished (http://localhost:8080). Initializing Live2D...');
            // 로컬 서버에서 로딩하므로 CORS 이슈 없이 즉시 초기화 시도
            _webController.runJavaScript('if(window.live2dManager) window.live2dManager.initialize(\'live2d-canvas\', \'$_modelPath\')');
          },
          onWebResourceError: (WebResourceError error) {
            logger.e('🎭 [Mobile] WebResourceError: ${error.description}');
          },
        ),
      )
      ..setOnConsoleMessage((JavaScriptConsoleMessage message) {
        final level = message.level;
        final msg = '🎭 [Mobile-WebView] ${message.message}';
        if (level == JavaScriptLogLevel.error) {
          logger.e(msg);
        } else if (level == JavaScriptLogLevel.warning) {
          logger.w(msg);
        } else {
          logger.d(msg);
        }
      });

    // 안드로이드 보안 설정 (http 허용)
    if (_webController.platform is AndroidWebViewController) {
      final androidController = _webController.platform as AndroidWebViewController;
      // ignore: deprecated_member_use
      androidController.setAllowFileAccess(true);
      // ignore: deprecated_member_use
      androidController.setAllowContentAccess(true);
    }

    // [핵심] 로컬 서버 주소로 로드
    _webController.loadRequest(Uri.parse('http://localhost:8080/index.html'));
  }

  @override
  void playMotion(String group, int index) {
    _webController.runJavaScript('window.live2dManager.playMotion(\'$group\', $index)');
  }

  @override
  void setMouthOpen(double value) {
    _webController.runJavaScript('window.live2dManager.setMouthOpen($value)');
  }

  @override
  void setParameterValue(String id, double value) {
    _webController.runJavaScript('window.live2dManager.setParameterValue(\'$id\', $value)');
  }

  @override
  void startLipSync() {
    _webController.runJavaScript('window.live2dManager.startLipSync()');
  }

  @override
  void stopLipSync() {
    _webController.runJavaScript('window.live2dManager.stopLipSync()');
  }

  @override
  double getLipSyncValue() => 0.0;

  @override
  void startListeningPose() {
    _webController.runJavaScript('window.live2dManager.startListeningPose()');
  }

  @override
  void stopListeningPose() {
    _webController.runJavaScript('window.live2dManager.stopListeningPose()');
  }

  @override
  void dispose() {
    _webController.runJavaScript('window.live2dManager.destroy()');
  }

  @override
  Widget buildView() {
    return WebViewWidget(controller: _webController);
  }
}
