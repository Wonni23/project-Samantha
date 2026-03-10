// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// 채팅 메시지 목록의 상태를 관리하는 최신 Notifier

@ProviderFor(Chat)
final chatProvider = ChatProvider._();

/// 채팅 메시지 목록의 상태를 관리하는 최신 Notifier
final class ChatProvider extends $NotifierProvider<Chat, List<ChatMessage>> {
  /// 채팅 메시지 목록의 상태를 관리하는 최신 Notifier
  ChatProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'chatProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$chatHash();

  @$internal
  @override
  Chat create() => Chat();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(List<ChatMessage> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<List<ChatMessage>>(value),
    );
  }
}

String _$chatHash() => r'04cae77fd0bfad57326ee4a267f6205478512a92';

/// 채팅 메시지 목록의 상태를 관리하는 최신 Notifier

abstract class _$Chat extends $Notifier<List<ChatMessage>> {
  List<ChatMessage> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<List<ChatMessage>, List<ChatMessage>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<List<ChatMessage>, List<ChatMessage>>,
              List<ChatMessage>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
