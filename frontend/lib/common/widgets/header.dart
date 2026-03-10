import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/router/router_paths.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';
import 'package:go_router/go_router.dart';

class Header extends ConsumerWidget implements PreferredSizeWidget {
  final String? title;
  const Header({super.key, this.title});

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (title != null ? 40.0 : 0),
      ); // 제목이 있으면 높이 추가

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final isLoggedIn =
        authState.hasValue && authState.value == AuthStatus.loggedIn;

    return AppBar(
      title: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: () => context.go(AppRoutePaths.home),
          child: const Text(
            'project Samantha',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
      ),
      centerTitle: true,
      actions: [
        if (isLoggedIn)
          TextButton(
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
            },
            child: const Text('로그아웃', style: TextStyle(color: Colors.black)),
          )
        else ...[
          TextButton(
            onPressed: () {
              context.go(AppRoutePaths.login);
            },
            child: const Text('로그인', style: TextStyle(color: Colors.black)),
          ),
        ],
      ],
      bottom: title != null
          ? PreferredSize(
              preferredSize: const Size.fromHeight(40.0),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 8.0),
                alignment: Alignment.center,
                child: Text(
                  title!,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            )
          : null,
    );
  }
}
