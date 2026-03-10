import 'package:flutter/material.dart';
import 'package:frontend/common/widgets/default_layout.dart';
import 'package:frontend/features/memory/ui/widgets/memory_view.dart';

class MemoryPage extends StatelessWidget {
  const MemoryPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const DefaultLayout(
      child: MemoryView(),
    );
  }
}
