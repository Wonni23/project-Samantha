import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/memory/data/models/user_context.dart';
import 'package:frontend/features/memory/providers/user_context_provider.dart';

class UserContextView extends ConsumerWidget {
  const UserContextView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contextState = ref.watch(userContextProvider);

    return contextState.when(
      data: (userContext) {
        return RefreshIndicator(
          onRefresh: () => ref.read(userContextProvider.notifier).refresh(),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildSectionTitle('나의 페르소나 상태'),
              _buildPersonaCard(context, userContext.personaState),
              const SizedBox(height: 24),
              _buildSectionTitle('AI가 부르는 나의 호칭'),
              _buildTitleCard(userContext.userTitle),
              const SizedBox(height: 24),
              _buildSectionTitle('수집된 사용자 프로필'),
              _buildProfileCard(userContext.userProfile),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            const Text(
              '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.',
              style: TextStyle(color: Colors.black87),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.read(userContextProvider.notifier).refresh(),
              child: const Text('다시 시도'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: Colors.black87,
        ),
      ),
    );
  }

  Widget _buildPersonaCard(BuildContext context, PersonaState persona) {
    return Card(
      color: Colors.black.withValues(alpha: 0.05),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildAxisRow(context, '장난스러움', persona.axisPlayful),
            _buildAxisRow(context, '거침없음', persona.axisFeisty),
            _buildAxisRow(context, '의존적임', persona.axisDependent),
            _buildAxisRow(context, '돌봄지향', persona.axisCaregive),
            _buildAxisRow(context, '성찰적임', persona.axisReflective),
          ],
        ),
      ),
    );
  }

  Widget _buildAxisRow(BuildContext context, String label, double value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: const TextStyle(color: Colors.black54, fontSize: 14),
              ),
              Text(
                '${(value * 100).toInt()}%',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.secondary,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: value,
            backgroundColor: Colors.black12,
            valueColor: AlwaysStoppedAnimation<Color>(Theme.of(context).colorScheme.secondary),
            borderRadius: BorderRadius.circular(4),
          ),
        ],
      ),
    );
  }

  Widget _buildTitleCard(String title) {
    return Card(
      color: Colors.black.withValues(alpha: 0.05),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        leading: const Icon(Icons.stars, color: Colors.amber),
        title: Text(
          title,
          style: const TextStyle(
            color: Colors.black87,
            fontSize: 16,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildProfileCard(Map<String, dynamic> profile) {
    if (profile.isEmpty) {
      return const Card(
        color: Colors.black12,
        elevation: 0,
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            '아직 수집된 정보가 없습니다.',
            style: TextStyle(color: Colors.black45),
          ),
        ),
      );
    }

    return Card(
      color: Colors.black.withValues(alpha: 0.05),
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          children: profile.entries.map((e) {
            return ListTile(
              dense: true,
              title: Text(
                e.key,
                style: const TextStyle(color: Colors.black54),
              ),
              trailing: Text(
                e.value.toString(),
                style: const TextStyle(
                  color: Colors.black87,
                  fontWeight: FontWeight.w500,
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}
