import 'package:frontend/features/chat/data/models/chat_message.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'chat_provider.g.dart';

/// 채팅 메시지 목록의 상태를 관리하는 최신 Notifier
@Riverpod(keepAlive: true)
class Chat extends _$Chat {
  @override
  List<ChatMessage> build() {
    ref.keepAlive();
    return [];
  }

  /// 새로운 메시지를 목록에 추가합니다.
  void addMessage(ChatMessage message) {
    state = [...state, message];
  }

  /// 봇의 마지막 메시지 내용을 스트리밍 텍스트로 업데이트합니다.
  void updateLastBotMessage(String textChunk) {
    if (textChunk.isEmpty) return;

    if (state.isNotEmpty) {
      final index = state.lastIndexWhere((m) => !m.isUser);
      if (index != -1) {
        final lastMessage = state[index];
        final String newContent;

        if (lastMessage.message == '...') {
          newContent = textChunk;
        } else {
          newContent = lastMessage.message + textChunk;
        }

        final updatedMessage = lastMessage.copyWith(message: newContent);
        final newState = List<ChatMessage>.from(state);
        newState[index] = updatedMessage;
        state = newState;
      }
    }
  }

  /// 텍스트 메시지를 리스트에 추가 (isUser 기반)
  void addUserMessage(String message) {
    addMessage(ChatMessage(message: message, isUser: true));
  }
}
