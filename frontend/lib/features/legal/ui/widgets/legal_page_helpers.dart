import 'package:flutter/material.dart';

Widget buildSection({required String title, required List<Widget> children}) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
      const SizedBox(height: 12),
      ...children,
      const SizedBox(height: 24),
    ],
  );
}

Widget buildParagraph(String text) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 8.0),
    child: Text(
      text,
      style: const TextStyle(fontSize: 15, height: 1.6),
    ),
  );
}

Widget buildListItem(String text) {
  return Padding(
    padding: const EdgeInsets.only(left: 16.0, bottom: 6.0),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('• ', style: TextStyle(fontSize: 15, height: 1.6)),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 15, height: 1.6),
          ),
        ),
      ],
    ),
  );
}
