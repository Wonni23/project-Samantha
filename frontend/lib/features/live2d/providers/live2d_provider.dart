import 'dart:async';
import 'package:frontend/core/network/socket_service.dart';
import 'package:frontend/features/chat/data/models/live2d_event.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'live2d_provider.g.dart';

@riverpod
class Live2DNotifier extends _$Live2DNotifier {
  StreamSubscription<Live2DEvent>? _subscription;

  @override
  Live2DEvent? build() {
    final socketService = ref.watch(socketServiceProvider);
    
    // 이전 구독 해제
    _subscription?.cancel();
    
    // 소켓 이벤트 스트림 구독
    _subscription = socketService.onLive2DEvent.listen((event) {
      state = event;
    });

    ref.onDispose(() {
      _subscription?.cancel();
    });

    return null;
  }

  /// 명시적으로 표정 업데이트 (필요 시)
  void updateEvent(Live2DEvent event) {
    state = event;
  }
}
