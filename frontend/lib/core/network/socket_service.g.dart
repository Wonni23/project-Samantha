// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'socket_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// 소켓의 실시간 상태를 제공하는 Notifier

@ProviderFor(SocketStatusNotifier)
final socketStatusProvider = SocketStatusNotifierProvider._();

/// 소켓의 실시간 상태를 제공하는 Notifier
final class SocketStatusNotifierProvider
    extends $NotifierProvider<SocketStatusNotifier, SocketStatus> {
  /// 소켓의 실시간 상태를 제공하는 Notifier
  SocketStatusNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'socketStatusProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$socketStatusNotifierHash();

  @$internal
  @override
  SocketStatusNotifier create() => SocketStatusNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SocketStatus value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SocketStatus>(value),
    );
  }
}

String _$socketStatusNotifierHash() =>
    r'14ac8536c6c61c7a5fbfe532b00360866d8e0749';

/// 소켓의 실시간 상태를 제공하는 Notifier

abstract class _$SocketStatusNotifier extends $Notifier<SocketStatus> {
  SocketStatus build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<SocketStatus, SocketStatus>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<SocketStatus, SocketStatus>,
              SocketStatus,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}

/// 소켓 에러 메시지를 제공하는 Notifier (UI에서 SnackBar 표시용)

@ProviderFor(SocketErrorNotifier)
final socketErrorProvider = SocketErrorNotifierProvider._();

/// 소켓 에러 메시지를 제공하는 Notifier (UI에서 SnackBar 표시용)
final class SocketErrorNotifierProvider
    extends $NotifierProvider<SocketErrorNotifier, String?> {
  /// 소켓 에러 메시지를 제공하는 Notifier (UI에서 SnackBar 표시용)
  SocketErrorNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'socketErrorProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$socketErrorNotifierHash();

  @$internal
  @override
  SocketErrorNotifier create() => SocketErrorNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(String? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<String?>(value),
    );
  }
}

String _$socketErrorNotifierHash() =>
    r'6fbb332949d2cf0973d2aeaa6af0e7020c1b0fd7';

/// 소켓 에러 메시지를 제공하는 Notifier (UI에서 SnackBar 표시용)

abstract class _$SocketErrorNotifier extends $Notifier<String?> {
  String? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<String?, String?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<String?, String?>,
              String?,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
