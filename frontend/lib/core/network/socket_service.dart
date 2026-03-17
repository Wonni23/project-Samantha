import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/utils/logger.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';
import 'package:frontend/features/chat/data/models/live2d_event.dart';
import 'package:socket_io_client/socket_io_client.dart' as io;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:frontend/core/utils/platform_utils_stub.dart' as web if (dart.library.js_interop) 'package:web/web.dart';

part 'socket_service.g.dart';

/// 소켓 연결 상태를 나타내는 열거형
enum SocketStatus { initial, connecting, connected, disconnected, error }

/// SocketService를 제공하는 Provider
final socketServiceProvider = Provider<SocketService>((ref) {
  final service = SocketService(ref);
  ref.onDispose(() => service.dispose());
  return service;
});

/// 소켓의 실시간 상태를 제공하는 Notifier
@riverpod
class SocketStatusNotifier extends _$SocketStatusNotifier {
  @override
  SocketStatus build() {
    final service = ref.watch(socketServiceProvider);

    // 상태 변경 스트림 구독
    final subscription = service.onStatusChanged.listen((status) {
      state = status;
    });

    ref.onDispose(() => subscription.cancel());

    return service.currentStatus;
  }
}

/// 소켓 에러 메시지를 제공하는 Notifier (UI에서 SnackBar 표시용)
@riverpod
class SocketErrorNotifier extends _$SocketErrorNotifier {
  @override
  String? build() {
    final service = ref.watch(socketServiceProvider);

    final subscription = service.onErrorOccurred.listen((error) {
      state = error;
    });

    ref.onDispose(() => subscription.cancel());

    return null;
  }

  void clear() => state = null;
}

/// 앱의 Socket.IO 통신을 관리하는 서비스 클래스
class SocketService {
  final Ref _ref;
  io.Socket? _socket;

  // 이벤트 및 상태 스트림 컨트롤러
  final _textChunkController = StreamController<String>.broadcast();
  final _audioChunkController = StreamController<Uint8List>.broadcast();
  final _audioSegmentStartController = StreamController<int>.broadcast();
  final _audioSegmentEndController = StreamController<int>.broadcast();
  final _emotionController = StreamController<String>.broadcast();
  final _live2DController = StreamController<Live2DEvent>.broadcast();
  final _sttTextController = StreamController<String>.broadcast();
  final _responseDoneController = StreamController<void>.broadcast();
  final _statusController = StreamController<SocketStatus>.broadcast();
  final _errorController = StreamController<String>.broadcast();

  // 현재 상태 저장
  SocketStatus _currentStatus = SocketStatus.initial;

  // 이벤트 스트림 Getter
  Stream<String> get onTextChunk => _textChunkController.stream;
  Stream<Uint8List> get onAudioChunk => _audioChunkController.stream;
  Stream<int> get onAudioSegmentStart => _audioSegmentStartController.stream;
  Stream<int> get onAudioSegmentEnd => _audioSegmentEndController.stream;
  Stream<String> get onEmotion => _emotionController.stream;
  Stream<Live2DEvent> get onLive2DEvent => _live2DController.stream;
  Stream<String> get onSttText => _sttTextController.stream;
  Stream<void> get onResponseDone => _responseDoneController.stream;
  Stream<SocketStatus> get onStatusChanged => _statusController.stream;
  Stream<String> get onErrorOccurred => _errorController.stream;

  SocketStatus get currentStatus => _currentStatus;

  SocketService(this._ref);

  /// 소켓 연결을 초기화합니다.
  Future<void> init() async {
    if (_socket?.connected == true) {
      logger.d('Socket is already connected.');
      return;
    }

    _updateStatus(SocketStatus.connecting);

    // 저장된 Access Token을 가져옵니다.
    final accessToken = await _ref.read(authProvider.notifier).getAccessToken();

    if (accessToken == null) {
      logger.e('Socket connection failed: Access Token is null.');
      _updateStatus(SocketStatus.error);
      _errorController.add('인증 토큰이 없습니다. 다시 로그인해주세요.');
      return;
    }

    logger.i('Initializing socket connection...');

    String socketUrl;

    if (kIsWeb) {
      // 웹 환경: 현재 브라우저의 호스트를 기반으로 동적 생성
      final currentHost = web.window.location.host;
      final protocol = web.window.location.protocol == 'https:' ? 'https' : 'http';
      socketUrl = '$protocol://$currentHost';
    } else {
      // 안드로이드 환경: .env 설정 또는 에뮬레이터 IP 사용
      final envUrl = dotenv.env['BACKEND_URL'];
      socketUrl = envUrl ?? 'http://10.0.2.2:8000';
    }

    logger.i('Socket URL: $socketUrl');

    final options = io.OptionBuilder()
        .setTransports([
          'polling',
          'websocket',
        ]) // Socket.IO 기본 동작: polling으로 시작 후 가능한 경우 websocket으로 업그레이드
        .setPath('/ws/socket.io') // 백엔드에 설정된 소켓 경로
        .enableAutoConnect() // 자동 재연결 활성화
        .setReconnectionAttempts(5) // 최대 재연결 시도 횟수
        .setReconnectionDelay(2000) // 재연결 시도 간격 (2초)
        .setAuth({'token': accessToken}) // 인증 토큰 설정
        .build();

    _socket = io.io(socketUrl, options);

    _registerEventListeners();

    _socket!.connect();
  }

  /// 서버로부터 오는 이벤트를 수신 대기합니다.
  void _registerEventListeners() {
    if (_socket == null) return;

    _socket!.onConnect((_) {
      logger.i('✅ Socket connected: ${_socket!.id}');
      _updateStatus(SocketStatus.connected);
    });

    _socket!.onDisconnect((_) {
      logger.w('👋 Socket disconnected');
      _updateStatus(SocketStatus.disconnected);
    });

    _socket!.onConnectError((data) {
      logger.e('❌ Socket Connection Error: ${data.runtimeType}');
      _updateStatus(SocketStatus.error);
      _errorController.add('서버 연결에 실패했습니다. 네트워크를 확인해주세요.');
    });

    _socket!.onError((data) {
      logger.e('❌ Socket error: ${data.runtimeType}');
      _errorController.add('통신 중 오류가 발생했습니다.');
    });

    _socket!.on(
      'connection_ack',
      (data) => logger.i('🤝 Connection acknowledged'),
    );
    _socket!.on('audio_ack', (data) => logger.d('🎤 Audio acknowledged'));

    // 서버로부터 오는 데이터 스트림
    _socket!.on('bot_text_chunk', (data) {
      final payload = _asEventMap(data);
      final text = payload?['text'];
      if (text is String && text.isNotEmpty) {
        _textChunkController.add(text);
      }
    });
    _socket!.on('bot_audio_chunk', (data) {
      final payload = _asEventMap(data);
      if (payload == null) {
        logger.w('bot_audio_chunk payload is invalid');
        return;
      }

      final raw = payload['data'];
      if (raw is Uint8List) {
        _audioChunkController.add(raw);
        return;
      }
      if (raw is List<int>) {
        _audioChunkController.add(Uint8List.fromList(raw));
        return;
      }
      if (raw is List) {
        final bytes = raw
            .whereType<num>()
            .map((v) => v.toInt())
            .where((v) => v >= 0 && v <= 255)
            .toList();
        if (bytes.isNotEmpty) {
          _audioChunkController.add(Uint8List.fromList(bytes));
        } else {
          logger.w('Skipped empty/invalid bot_audio_chunk payload.');
        }
      }
    });

    _socket!.on('bot_audio_segment_start', (data) {
      final payload = _asEventMap(data);
      if (payload == null) return;
      final raw = payload['segment_index'];
      if (raw is int) {
        _audioSegmentStartController.add(raw);
      } else if (raw is num) {
        _audioSegmentStartController.add(raw.toInt());
      }
    });

    _socket!.on('bot_audio_segment_end', (data) {
      final payload = _asEventMap(data);
      if (payload == null) return;
      final raw = payload['segment_index'];
      if (raw is int) {
        _audioSegmentEndController.add(raw);
      } else if (raw is num) {
        _audioSegmentEndController.add(raw.toInt());
      }
    });

    _socket!.on('bot_emotion', (data) {
      final payload = _asEventMap(data);
      final emotion = payload?['emotion'];
      if (emotion is String && emotion.isNotEmpty) {
        _emotionController.add(emotion);
      }
    });

    _socket!.on('bot_live2d', (data) {
      try {
        final payload = _asEventMap(data);
        if (payload == null) {
          logger.w('bot_live2d payload is not Map');
          return;
        }

        final normalized = Map<String, dynamic>.from(payload);
        normalized['expression'] =
            (normalized['expression'] as String?) ?? 'serene';

        final event = Live2DEvent.fromJson(normalized);
        _live2DController.add(event);
      } catch (e) {
        logger.e('Failed to parse bot_live2d event: ${e.runtimeType}');
      }
    });

    _socket!.on('stt_text', (data) {
      final payload = _asEventMap(data);
      final text = payload?['text'];
      if (text is String && text.isNotEmpty) {
        _sttTextController.add(text);
      }
    });

    _socket!.on('bot_response_done', (_) => _responseDoneController.add(null));

    // 서버가 보내는 비즈니스 로직 에러 처리
    _socket!.on('error', (data) {
      logger.e('🛑 Received server error');
      final payload = _asEventMap(data);
      final serverMessage = payload?['msg'];
      if (serverMessage is String && serverMessage.isNotEmpty) {
        _errorController.add(serverMessage);
        return;
      }

      final fallbackMessage = payload?['message'];
      if (fallbackMessage is String && fallbackMessage.isNotEmpty) {
        _errorController.add(fallbackMessage);
        return;
      }

      if (data is String && data.isNotEmpty) {
        _errorController.add(data);
        return;
      }

      _errorController.add('통신 중 오류가 발생했습니다.');
    });
  }

  /// 상태를 업데이트하고 스트림에 알립니다.
  void _updateStatus(SocketStatus status) {
    _currentStatus = status;
    _statusController.add(status);
  }

  /// 녹음된 음성 데이터를 서버로 전송합니다.
  void sendAudio(Uint8List audioData) {
    if (_socket?.connected == true) {
      _socket!.emit('audio_blob', audioData);
      logger.d('Audio blob sent (${audioData.length} bytes).');
    } else {
      logger.w('Cannot send audio. Socket is not connected.');
      _errorController.add('서버와 연결되어 있지 않아 음성을 보낼 수 없습니다.');
      // 필요 시 여기서 수동 재연결 시도 가능
      if (_currentStatus != SocketStatus.connecting) {
        init();
      }
    }
  }

  /// 텍스트 메시지를 서버로 전송합니다.
  void sendTextMessage(String text) {
    if (_socket?.connected == true) {
      _socket!.emit('text_message', {'text': text});
      logger.d('Text message sent: $text');
    } else {
      logger.w('Cannot send text. Socket is not connected.');
      _errorController.add('서버와 연결되어 있지 않아 메시지를 보낼 수 없습니다.');
      if (_currentStatus != SocketStatus.connecting) {
        init();
      }
    }
  }

  /// 서비스 종료 시 소켓 연결을 해제합니다.
  void dispose() {
    logger.i('Disconnecting socket...');
    _textChunkController.close();
    _audioChunkController.close();
    _audioSegmentStartController.close();
    _audioSegmentEndController.close();
    _emotionController.close();
    _live2DController.close();
    _sttTextController.close();
    _responseDoneController.close();
    _statusController.close();
    _errorController.close();
    _socket?.dispose();
    _socket = null;
  }

  Map<String, dynamic>? _asEventMap(dynamic data) {
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    if (data is List && data.isNotEmpty) {
      final first = data.first;
      if (first is Map<String, dynamic>) {
        return first;
      }
      if (first is Map) {
        return Map<String, dynamic>.from(first);
      }
    }
    return null;
  }
}
