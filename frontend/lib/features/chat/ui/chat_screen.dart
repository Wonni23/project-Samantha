import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/chat/providers/chat_provider.dart';
import 'package:frontend/features/home/providers/ai_response_provider.dart';
import 'package:frontend/features/home/providers/audio_recorder_provider.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _focusNode.requestFocus();
    _controller.addListener(_onTextChanged);
    // 초기 로드 시 하단 스크롤
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onTextChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  /// 하단으로 자동 스크롤
  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  /// 텍스트 메시지 전송 로직
  void _sendTextMessage() {
    if (_controller.text.trim().isEmpty) return;
    
    // [수정] 전체 프로세스 진행 중이면 전송 방지
    final aiState = ref.read(aIResponseProvider);
    if (aiState.isProcessing) return;

    // ChatNotifier 대신 AIResponseNotifier의 sendTextMessage 호출
    ref.read(aIResponseProvider.notifier).sendTextMessage(_controller.text);
    _controller.clear();
    _focusNode.unfocus();
  }

  /// [수정] 음성 메시지 처리 책임을 AIResponseNotifier로 위임
  Future<void> _handleVoiceMessage() async {
    final audioNotifier = ref.read(audioRecorderProvider.notifier);
    final audioState = ref.read(audioRecorderProvider);
    
    final aiState = ref.read(aIResponseProvider);
    final aiNotifier = ref.read(aIResponseProvider.notifier);

    if (audioState.isRecording) {
      // 1. 녹음 중지
      await audioNotifier.stopRecording();

      // 2. 녹음된 오디오 데이터 가져오기
      final audioBytes = await audioNotifier.getRecordedAudioBytes();

      // 3. AI 응답 요청 (모든 채팅 메시지 처리는 이제 AIResponseNotifier가 담당)
      if (audioBytes != null) {
        await aiNotifier.getAIResponse(audioBytes);
      }

      // 4. 녹음 UI 상태 초기화
      audioNotifier.clearRecording();
    } else {
      // [수정] 전체 프로세스 진행 중이면 녹음 시작 불가
      if (audioState.isPlaying || aiState.isProcessing) { 
        return;
      }

      // 녹음 시작
      aiNotifier.clearAIResponse(); // 이전 AI 응답 상태 초기화
      await audioNotifier.startRecording();
    }
  }

  @override
  Widget build(BuildContext context) {
    // --- Provider 상태 구독 ---
    final allMessages = ref.watch(chatProvider);
    final audioState = ref.watch(audioRecorderProvider);
    // aIResponseProvider는 non-nullable AIResponseState를 반환함
    final aiState = ref.watch(aIResponseProvider); 

    // [수정] AI 응답 전체 프로세스(isProcessing) 완료 전까지는 busy 상태 유지
    final bool isBusy = aiState.isProcessing || audioState.isPlaying; 

    // 메시지가 추가될 때마다 하단 스크롤 실행
    ref.listen(chatProvider, (previous, next) {
      if (previous?.length != next.length) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
      }
    });

    // AI 응답 상태 변화 감지 및 포커스 재설정
    ref.listen(aIResponseProvider, (previousAiState, newAiState) {
      // [수정] 개별 청크가 아닌 전체 프로세스(isProcessing)가 끝났을 때만 포커스 요청
      final wasProcessing = previousAiState?.isProcessing ?? false;
      final isNowFinished = !newAiState.isProcessing;

      if (wasProcessing && isNowFinished) {
        // AI 활동이 완전히 끝난 후 텍스트 필드에 포커스 재설정
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted && _focusNode.canRequestFocus) {
            _focusNode.requestFocus();
          }
        });
      }
    });

    return Padding(
      padding: const EdgeInsets.all(20.0),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.black.withAlpha(128),
          borderRadius: BorderRadius.circular(10.0),
          border: Border.all(color: Colors.white, width: 1.0),
        ),
        child: Column(
          children: [
            // --- 메시지 목록 UI ---
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                itemCount: allMessages.length,
                reverse: false, // 일반적인 채팅처럼 아래로 쌓이도록 변경
                itemBuilder: (context, index) {
                  final message = allMessages[index];
                  return _buildMessageBubble(message.message, message.isUser);
                },
              ),
            ),
            // --- 입력창 및 버튼 UI ---
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      focusNode: _focusNode,
                      controller: _controller,
                      enabled: !isBusy, // isBusy 변수 사용
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: audioState.isRecording
                            ? '녹음 중... 다시 눌러 전송'
                            : (isBusy
                                ? '응답을 기다리는 중...'
                                : '메시지를 입력하거나 마이크를 누르세요'),
                        hintStyle: const TextStyle(color: Colors.white70),
                        border: const OutlineInputBorder(
                          borderSide: BorderSide(color: Colors.white),
                        ),
                        enabledBorder: const OutlineInputBorder(
                          borderSide: BorderSide(color: Colors.white),
                        ),
                        focusedBorder: const OutlineInputBorder(
                          borderSide: BorderSide(color: Colors.white),
                        ),
                        disabledBorder: const OutlineInputBorder(
                          borderSide: BorderSide(color: Colors.white24),
                        ),
                      ),
                      onSubmitted: (_) {
                        _sendTextMessage();
                        _focusNode.unfocus();
                      },
                    ),
                  ),
                  // 텍스트 전송 버튼
                  IconButton(
                    icon: const Icon(Icons.send, color: Colors.white),
                    onPressed: (isBusy || _controller.text.trim().isEmpty) ? null : _sendTextMessage,
                    disabledColor: Colors.white24,
                  ),
                  // 음성 녹음/전송 버튼
                  IconButton(
                    icon: Icon(
                      audioState.isRecording ? Icons.stop_circle : Icons.mic,
                      color: audioState.isRecording
                          ? Colors.redAccent
                          : (isBusy ? Colors.white24 : Colors.white),
                      size: 28,
                    ),
                    onPressed: _handleVoiceMessage,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageBubble(String message, bool isUser) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
        decoration: BoxDecoration(
          color: isUser ? Colors.blue[300] : Colors.grey[700],
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(message, style: const TextStyle(color: Colors.white)),
      ),
    );
  }
}
