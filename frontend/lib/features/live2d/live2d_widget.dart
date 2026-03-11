// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:js_interop';
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:web/web.dart' as web;

// Live2D Manager JavaScript 객체 정의
extension type Live2DManager._(JSObject _) implements JSObject {
  external JSPromise<JSAny?> initialize(String canvasId, String modelPath);
  external void playMotion(String group, int index);
  external void setMouthOpen(double value);
  external void setParameterValue(String id, double value);
  // [신규] 립싱크 제어 메서드 추가
  external void startLipSync();
  external void stopLipSync();
  external double getLipSyncValue();
  // [신규] 커스텀 포즈 제어
  external void startListeningPose();
  external void stopListeningPose();
  external void destroy();
}

// Window 객체 확장
@JS()
extension type _WindowExtension._(web.Window _) implements web.Window {
  external Live2DManager? get live2dManager;
}

extension WindowLive2DExtension on web.Window {
  Live2DManager? get live2dManager => (_WindowExtension._(this)).live2dManager;
}

/// Live2D 모델을 표시하는 Flutter Widget
class Live2DWidget extends ConsumerStatefulWidget {
  /// Live2D 모델의 경로 (예: 'live2d_model/model.model3.json')
  final String modelPath;

  /// 위젯의 너비
  final double? width;

  /// 위젯의 높이
  final double? height;

  const Live2DWidget({
    super.key,
    required this.modelPath,
    this.width,
    this.height,
  });

  @override
  ConsumerState<Live2DWidget> createState() => Live2DWidgetState();
}

class Live2DWidgetState extends ConsumerState<Live2DWidget> {
  static int _viewIdCounter = 0;
  late String _viewId;
  late String _canvasId;

  @override
  void initState() {
    super.initState();
    _viewId = 'live2d-view-${_viewIdCounter++}';
    _canvasId = 'live2d-canvas-$_viewId';

    // HTML 요소 등록
    _registerHtmlElement();
  }

  void _registerHtmlElement() {
    // Canvas 요소 생성
    final canvas = web.document.createElement('canvas') as web.HTMLCanvasElement
      ..id = _canvasId
      ..style.width = '100%'
      ..style.height = '100%';

    // 컨테이너 div 생성
    final container = web.document.createElement('div') as web.HTMLDivElement
      ..id = _viewId
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.backgroundColor = '#EFEBE0' // 더욱 깊이감 있는 모던 코지 오트밀
      ..appendChild(canvas);

    // Flutter에 HTML 요소 등록
    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int viewId) {
      // Live2D 초기화
      _initializeLive2D();
      return container;
    });
  }

  void _initializeLive2D() {
    // JavaScript 함수 호출하여 Live2D 초기화
    logger.i('🎭 Attempting to initialize Live2D widget...');
    Future.delayed(const Duration(milliseconds: 100), () {
      try {
        logger.i('🎭 Checking Live2D manager availability...');
        final manager = web.window.live2dManager;
        if (manager != null) {
          logger.i('🎭 Live2D manager found, initializing with canvas: $_canvasId');
          manager.initialize(_canvasId, widget.modelPath);
        } else {
          logger.e('🎭 Live2D manager not found in window object');
        }
      } catch (e) {
        logger.e('🎭 Failed to initialize Live2D', error: e);
      }
    });
  }

  /// 모션 재생
  void playMotion(String group, [int index = 0]) {
    try {
      final manager = web.window.live2dManager;
      manager?.playMotion(group, index);
      logger.d('Live2D motion played: group=$group, index=$index');
    } catch (e) {
      logger.e('Failed to play motion', error: e);
    }
  }

  /// 입 모양 조절 (0.0 ~ 1.0)
  void setMouthOpen(double value) {
    try {
      final manager = web.window.live2dManager;
      manager?.setMouthOpen(value);
    } catch (e) {
      logger.e('Failed to set mouth open', error: e);
    }
  }

  /// 파라미터 값 직접 설정
  void setParameterValue(String id, double value) {
    try {
      final manager = web.window.live2dManager;
      manager?.setParameterValue(id, value);
    } catch (e) {
      logger.e('Failed to set parameter value', error: e);
    }
  }

  /// [신규] 립싱크 시작 (인터셉터가 오디오 그래프를 자동 처리)
  void startLipSync() {
    try {
      final manager = web.window.live2dManager;
      manager?.startLipSync();
    } catch (e) {
      logger.e('Failed to start lip-sync', error: e);
    }
  }

  /// [신규] 립싱크 중지
  void stopLipSync() {
    try {
      final manager = web.window.live2dManager;
      manager?.stopLipSync();
    } catch (e) {
      logger.e('Failed to stop lip-sync', error: e);
    }
  }

  /// [신규] 귀 기울이는 자세 시작
  void startListeningPose() {
    try {
      final manager = web.window.live2dManager;
      manager?.startListeningPose();
    } catch (e) {
      logger.e('Failed to start listening pose', error: e);
    }
  }

  /// [신규] 커스텀 자세 해제
  void stopListeningPose() {
    try {
      final manager = web.window.live2dManager;
      manager?.stopListeningPose();
    } catch (e) {
      logger.e('Failed to stop listening pose', error: e);
    }
  }

  /// [신규] 실시간 진폭 값 가져오기
  double getLipSyncValue() {
    try {
      final manager = web.window.live2dManager;
      return manager?.getLipSyncValue() ?? 0.0;
    } catch (e) {
      return 0.0;
    }
  }

  @override
  void dispose() {
    // Live2D 정리
    try {
      final manager = web.window.live2dManager;
      manager?.destroy();
    } catch (e) {
      logger.e('Failed to destroy Live2D', error: e);
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.width ?? double.infinity,
      height: widget.height ?? 400,
      child: HtmlElementView(viewType: _viewId),
    );
  }
}
