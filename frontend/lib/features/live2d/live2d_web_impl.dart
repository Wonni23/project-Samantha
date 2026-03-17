import 'dart:async';
import 'dart:js_interop';
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;
import 'package:frontend/core/utils/logger.dart';
import 'live2d_controller.dart';

// Live2D Manager JavaScript 객체 정의
@JS()
extension type Live2DManager._(JSObject _) implements JSObject {
  external JSPromise<JSAny?> initialize(String canvasId, String modelPath);
  external void playMotion(String group, int index);
  external void setMouthOpen(double value);
  external void setParameterValue(String id, double value);
  external void startLipSync();
  external void stopLipSync();
  external double getLipSyncValue();
  external void startListeningPose();
  external void stopListeningPose();
  external void destroy();
}

// Window 객체 확장
@JS()
extension type WindowExtension._(web.Window _) implements web.Window {
  external Live2DManager? get live2dManager;
}

extension WindowLive2DExtension on web.Window {
  Live2DManager? get live2dManager => (WindowExtension._(this)).live2dManager;
}

class Live2DControllerImpl implements Live2DController {
  final String _viewId;
  final String _canvasId;
  final String _modelPath;

  Live2DControllerImpl(this._viewId, this._canvasId, this._modelPath) {
    _registerHtmlElement();
  }

  void _registerHtmlElement() {
    final canvas = web.document.createElement('canvas') as web.HTMLCanvasElement
      ..id = _canvasId
      ..style.width = '100%'
      ..style.height = '100%';

    final container = web.document.createElement('div') as web.HTMLDivElement
      ..id = _viewId
      ..style.width = '100%'
      ..style.height = '100%'
      ..style.backgroundColor = '#EFEBE0'
      ..appendChild(canvas);

    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int viewId) {
      _initializeLive2D();
      return container;
    });
  }

  void _initializeLive2D() {
    logger.i('🎭 [Web] Initializing Live2D widget...');
    Future.delayed(const Duration(milliseconds: 100), () {
      try {
        final manager = web.window.live2dManager;
        if (manager != null) {
          manager.initialize(_canvasId, _modelPath);
        }
      } catch (e) {
        logger.e('🎭 [Web] Failed to initialize Live2D', error: e);
      }
    });
  }

  @override
  void playMotion(String group, int index) => web.window.live2dManager?.playMotion(group, index);

  @override
  void setMouthOpen(double value) => web.window.live2dManager?.setMouthOpen(value);

  @override
  void setParameterValue(String id, double value) => web.window.live2dManager?.setParameterValue(id, value);

  @override
  void startLipSync() => web.window.live2dManager?.startLipSync();

  @override
  void stopLipSync() => web.window.live2dManager?.stopLipSync();

  @override
  double getLipSyncValue() => web.window.live2dManager?.getLipSyncValue() ?? 0.0;

  @override
  void startListeningPose() => web.window.live2dManager?.startListeningPose();

  @override
  void stopListeningPose() => web.window.live2dManager?.stopListeningPose();

  @override
  void dispose() => web.window.live2dManager?.destroy();

  @override
  Widget buildView() {
    return HtmlElementView(viewType: _viewId);
  }
}
