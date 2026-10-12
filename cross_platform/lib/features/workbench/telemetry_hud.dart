import 'package:flutter/material.dart';
import '../../core/services/telemetry_service.dart';

class TelemetryHudOverlay extends StatelessWidget {
  final bool isExpanded;
  final VoidCallback onToggleExpand;

  const TelemetryHudOverlay({
    super.key,
    this.isExpanded = true,
    required this.onToggleExpand,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: TelemetryService(),
      builder: (context, _) {
        final telemetry = TelemetryService();
        final latency = telemetry.currentLatencyMs;
        final fps = telemetry.currentFps;
        final dropped = telemetry.droppedFrames;
        final memory = telemetry.memoryUsageMb;
        final platform = telemetry.osPlatform;
        final backend = telemetry.renderingBackend;

        Color latencyColor = const Color(0xFF10B981); // Emerald
        if (latency > 30.0) {
          latencyColor = const Color(0xFFEF4444); // Red
        } else if (latency > 18.0) {
          latencyColor = const Color(0xFFF59E0B); // Amber
        }

        return Positioned(
          top: 16,
          left: 16,
          child: Material(
            color: Colors.transparent,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A).withOpacity(0.88),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFF38BDF8).withOpacity(0.4),
                  width: 1.2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.45),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Title Bar & Expand Toggle
                  InkWell(
                    onTap: onToggleExpand,
                    borderRadius: BorderRadius.circular(6),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: latencyColor,
                            boxShadow: [
                              BoxShadow(
                                color: latencyColor.withOpacity(0.6),
                                blurRadius: 6,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          "HARDWARE TELEMETRY HUD",
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 10,
                            letterSpacing: 1.2,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Icon(
                          isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                          size: 14,
                          color: const Color(0xFF94A3B8),
                        ),
                      ],
                    ),
                  ),

                  if (isExpanded) ...[
                    const SizedBox(height: 8),
                    Container(height: 1, width: 220, color: const Color(0xFF334155)),
                    const SizedBox(height: 8),

                    // Metrics Grid
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildMetricPill(
                          label: "LATENCY",
                          value: "${latency.toStringAsFixed(1)} ms",
                          color: latencyColor,
                        ),
                        const SizedBox(width: 10),
                        _buildMetricPill(
                          label: "FPS",
                          value: "${fps.toStringAsFixed(0)} FPS",
                          color: fps >= 55 ? const Color(0xFF38BDF8) : const Color(0xFFF59E0B),
                        ),
                        const SizedBox(width: 10),
                        _buildMetricPill(
                          label: "DROPS",
                          value: "$dropped",
                          color: dropped > 10 ? const Color(0xFFEF4444) : const Color(0xFF94A3B8),
                        ),
                      ],
                    ),

                    const SizedBox(height: 8),

                    // Memory & Architecture Info
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.memory_rounded, size: 12, color: Color(0xFFA855F7)),
                        const SizedBox(width: 4),
                        Text(
                          "RAM: ${memory.toStringAsFixed(1)} MB",
                          style: const TextStyle(
                            color: Color(0xFFCBD5E1),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 4),

                    // Backend badge
                    Container(
                      constraints: const BoxConstraints(maxWidth: 240),
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        "$platform • $backend",
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 9.5,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildMetricPill({
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF64748B),
            fontSize: 9,
            fontWeight: FontWeight.w600,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 14,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
