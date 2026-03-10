import 'package:flutter/material.dart';
import 'package:frontend/common/widgets/footer.dart';
import 'package:frontend/common/widgets/header.dart';

class DefaultLayout extends StatelessWidget {
  final Widget child;
  final Widget? bottomNavigationBar;

  const DefaultLayout({
    super.key,
    required this.child,
    this.bottomNavigationBar,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const Header(),
      body: Column(
        children: [
          Expanded(
            child: child,
          ),
          const Footer(),
        ],
      ),
      bottomNavigationBar: bottomNavigationBar,
    );
  }
}