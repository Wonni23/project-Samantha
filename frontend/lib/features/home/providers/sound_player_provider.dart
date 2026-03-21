import 'dart:async';
import 'dart:math'; // Random을 위해 추가
import 'package:flutter/material.dart';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'sound_player_provider.g.dart';

/// 앱 전체에서 공유될 단일 FlutterSoundPlayer 인스턴스를 관리하고 볼륨(Level) 상태를 제공하는 Notifier
@Riverpod(keepAlive: true)
class SoundPlayerNotifier extends _$SoundPlayerNotifier {
  late FlutterSoundPlayer _player;
  StreamSubscription? _progressSubscription;
  final _random = Random();
  double _lastVolume = 0.0;

  @override
  double build() {
    _player = FlutterSoundPlayer();
    _init();

    ref.onDispose(() {
      _progressSubscription?.cancel();
      _player.closePlayer();
    });

    return 0.0; // 초기 볼륨 상태 (0.0 ~ 1.0)
  }

  Future<void> _init() async {
    await _player.openPlayer();
    // 립싱크를 위해 30ms 단위로 업데이트 (너무 잦으면 WebView 부하 발생)
    await _player.setSubscriptionDuration(const Duration(milliseconds: 30));
  }

  /// 플레이어 인스턴스를 직접 반환합니다 (기존 코드 호환용).
  FlutterSoundPlayer get player => _player;

  /// 오디오 재생을 시작하고 볼륨 모니터링을 활성화합니다.
  Future<void> startPlayer({
    required String fromURI,
    Codec codec = Codec.defaultCodec,
    VoidCallback? whenFinished,
  }) async {
    await _player.startPlayer(
      fromURI: fromURI,
      codec: codec,
      whenFinished: () {
        _stopMetering();
        if (whenFinished != null) whenFinished();
      },
    );
    _startMetering();
  }

  /// 재생을 중지하고 볼륨 모니터링을 끕니다.
  Future<void> stopPlayer() async {
    await _player.stopPlayer();
    _stopMetering();
  }

  void _startMetering() {
    _progressSubscription?.cancel();
    _progressSubscription = _player.onProgress?.listen((e) {
      // 실제 말하는 것 같은 역동적인 입 움직임을 위해 노이즈 알고리즘 적용
      // 1. 기본적으로 0.3 ~ 1.0 사이를 빠르게 진동
      // 2. 가끔 입을 크게 벌리거나(1.0) 작게 벌리는(0.1) 변화를 줌
      double target;
      if (_random.nextDouble() > 0.8) {
        // 20% 확률로 입을 크게 벌리거나 거의 닫음 (음절의 끝이나 강조)
        target = _random.nextBool() ? 0.9 : 0.1;
      } else {
        // 80% 확률로 중간 범위에서 바쁘게 움직임
        target = 0.3 + _random.nextDouble() * 0.6;
      }

      // 이전 값과 보간하여 너무 튀지 않게 조절 (Smoothing)
      _lastVolume = _lastVolume * 0.3 + target * 0.7;
      state = _lastVolume;
    });
  }

  void _stopMetering() {
    _progressSubscription?.cancel();
    _lastVolume = 0.0;
    state = 0.0;
  }
}
