import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/services/telemetry_service.dart';

class CrashAndLogExporter extends StatefulWidget {
  const CrashAndLogExporter({super.key});

  @override
  State<CrashAndLogExporter> createState() => _CrashAndLogExporterState();
}

class _CrashAndLogExporterState extends State<CrashAndLogExporter> {
  LogSeverity? _filterSeverity;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: TelemetryService(),
      builder: (context, _) {
        final telemetry = TelemetryService();
        final rawLogs = telemetry.logs;

        // Apply filters
        final filteredLogs = rawLogs.where((entry) {
          if (_filterSeverity != null && entry.severity != _filterSeverity) {
            return false;
          }
          if (_searchController.text.isNotEmpty) {
            final query = _searchController.text.toLowerCase();
            return entry.message.toLowerCase().contains(query) ||
                entry.tag.toLowerCase().contains(query);
          }
          return true;
        }).toList();

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.terminal_rounded, color: Color(0xFF10B981), size: 18),
                      SizedBox(width: 8),
                      Text(
                        "CRASH & DIAGNOSTIC LOG EXPORTER",
                        style: TextStyle(
                          color: Color(0xFFE2E8F0),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      TextButton.icon(
                        onPressed: () => telemetry.clearLogs(),
                        icon: const Icon(Icons.delete_sweep_outlined, size: 14, color: Color(0xFF94A3B8)),
                        label: const Text("Clear", style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        onPressed: () => _copyDiagnosticBundle(context, telemetry),
                        icon: const Icon(Icons.copy_all_rounded, size: 14),
                        label: const Text("Copy Diagnostic Bundle", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0284C7),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                      ),
                    ],
                  ),
                ],
              ),

              const SizedBox(height: 12),

              // Filter Controls
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      onChanged: (_) => setState(() {}),
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                      decoration: InputDecoration(
                        hintText: "Filter logs by tag or keyword...",
                        hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                        prefixIcon: const Icon(Icons.search, size: 16, color: Color(0xFF64748B)),
                        isDense: true,
                        filled: true,
                        fillColor: const Color(0xFF0F172A),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: const BorderSide(color: Color(0xFF334155)),
                        ),
                        contentPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  DropdownButton<LogSeverity?>(
                    value: _filterSeverity,
                    dropdownColor: const Color(0xFF0F172A),
                    style: const TextStyle(fontSize: 11, color: Color(0xFFCBD5E1)),
                    underline: const SizedBox(),
                    items: const [
                      DropdownMenuItem(value: null, child: Text("All Severities")),
                      DropdownMenuItem(value: LogSeverity.info, child: Text("Info")),
                      DropdownMenuItem(value: LogSeverity.warning, child: Text("Warnings")),
                      DropdownMenuItem(value: LogSeverity.error, child: Text("Errors")),
                    ],
                    onChanged: (val) {
                      setState(() {
                        _filterSeverity = val;
                      });
                    },
                  ),
                ],
              ),

              const SizedBox(height: 12),

              // Log Terminal Console
              Container(
                height: 180,
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF0A0F1D),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF1E293B)),
                ),
                child: filteredLogs.isEmpty
                    ? const Center(
                        child: Text(
                          "No log records match current filter.",
                          style: TextStyle(color: Color(0xFF475569), fontSize: 11),
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        itemCount: filteredLogs.length,
                        itemBuilder: (context, index) {
                          final entry = filteredLogs[index];
                          Color badgeColor = const Color(0xFF38BDF8); // info
                          if (entry.severity == LogSeverity.warning) {
                            badgeColor = const Color(0xFFF59E0B);
                          } else if (entry.severity == LogSeverity.error ||
                              entry.severity == LogSeverity.critical) {
                            badgeColor = const Color(0xFFEF4444);
                          }

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}:${entry.timestamp.second.toString().padLeft(2, '0')}",
                                  style: const TextStyle(
                                    color: Color(0xFF475569),
                                    fontSize: 10,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                  decoration: BoxDecoration(
                                    color: badgeColor.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(
                                    entry.severity.name.toUpperCase(),
                                    style: TextStyle(
                                      color: badgeColor,
                                      fontSize: 9,
                                      fontWeight: FontWeight.bold,
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  "[${entry.tag}]",
                                  style: const TextStyle(
                                    color: Color(0xFF94A3B8),
                                    fontSize: 10,
                                    fontWeight: FontWeight.w600,
                                    fontFamily: 'monospace',
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    entry.message,
                                    style: const TextStyle(
                                      color: Color(0xFFE2E8F0),
                                      fontSize: 10.5,
                                      fontFamily: 'monospace',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _copyDiagnosticBundle(BuildContext context, TelemetryService telemetry) {
    final bundle = telemetry.generateDiagnosticBundle();
    Clipboard.setData(ClipboardData(text: bundle));

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Row(
          children: [
            Icon(Icons.check_circle, color: Color(0xFF10B981), size: 18),
            SizedBox(width: 8),
            Text("Diagnostic Bundle copied to system clipboard!"),
          ],
        ),
        backgroundColor: const Color(0xFF0F172A),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}
