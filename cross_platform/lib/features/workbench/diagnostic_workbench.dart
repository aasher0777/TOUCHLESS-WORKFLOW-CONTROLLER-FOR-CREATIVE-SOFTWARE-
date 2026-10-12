import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../../core/services/telemetry_service.dart';
import '../../core/models/landmark_model.dart';
import '../../platform/camera_service.dart';
import 'input_simulator.dart';
import 'log_exporter.dart';

class DiagnosticWorkbenchModal extends StatefulWidget {
  final CameraService cameraService;
  final Function(HandLandmarksResult simulatedResult)? onSimulatedFrame;
  final bool isHudVisible;
  final ValueChanged<bool> onToggleHud;

  const DiagnosticWorkbenchModal({
    super.key,
    required this.cameraService,
    this.onSimulatedFrame,
    required this.isHudVisible,
    required this.onToggleHud,
  });

  static Future<void> show(
    BuildContext context, {
    required CameraService cameraService,
    Function(HandLandmarksResult simulatedResult)? onSimulatedFrame,
    required bool isHudVisible,
    required ValueChanged<bool> onToggleHud,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => DiagnosticWorkbenchModal(
        cameraService: cameraService,
        onSimulatedFrame: onSimulatedFrame,
        isHudVisible: isHudVisible,
        onToggleHud: onToggleHud,
      ),
    );
  }

  @override
  State<DiagnosticWorkbenchModal> createState() => _DiagnosticWorkbenchModalState();
}

class _DiagnosticWorkbenchModalState extends State<DiagnosticWorkbenchModal> {
  ResolutionPreset _selectedPreset = ResolutionPreset.medium;
  int _selectedCamIndex = 0;
  bool _isSwitchingCamera = false;

  @override
  void initState() {
    super.initState();
    _selectedCamIndex = widget.cameraService.selectedCameraIndex;
  }

  @override
  Widget build(BuildContext context) {
    final cameras = widget.cameraService.availableCameras;

    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A), // Dark slate
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: Color(0xFF38BDF8), width: 1.5),
        ),
      ),
      child: Column(
        children: [
          // Header Drag Handle
          Container(
            margin: const EdgeInsets.only(top: 12, bottom: 8),
            width: 48,
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFF334155),
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Title & Dismiss
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0284C7).withOpacity(0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.developer_mode_rounded, color: Color(0xFF38BDF8), size: 20),
                    ),
                    const SizedBox(width: 12),
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "DIAGNOSTIC & TESTING WORKBENCH",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        Text(
                          "Cross-Platform Developer Tools & Device Controls",
                          style: TextStyle(color: Color(0xFF64748B), fontSize: 11),
                        ),
                      ],
                    ),
                  ],
                ),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),

          const Divider(color: Color(0xFF1E293B), height: 1),

          // Scrollable Workbench Content
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // 1. Camera Stream & Resolution Switcher Card
                _buildCameraSwitcherCard(cameras),

                const SizedBox(height: 16),

                // 2. HUD Visibility & Telemetry Quick Toggle
                _buildHudToggleCard(),

                const SizedBox(height: 16),

                // 3. Cross-Platform Input Simulator
                CrossPlatformInputSimulator(
                  onSimulatedFrame: widget.onSimulatedFrame,
                ),

                const SizedBox(height: 16),

                // 4. Crash & Diagnostic Log Exporter
                const CrashAndLogExporter(),

                const SizedBox(height: 24),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraSwitcherCard(List<CameraDescription> cameras) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.videocam_rounded, color: Color(0xFFF59E0B), size: 18),
              SizedBox(width: 8),
              Text(
                "CAMERA STREAM & RESOLUTION SWITCHER",
                style: TextStyle(
                  color: Color(0xFFE2E8F0),
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          Row(
            children: [
              // Hardware Camera Selector
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Active Sensor / USB Device",
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF334155)),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int>(
                          isExpanded: true,
                          value: _selectedCamIndex < cameras.length ? _selectedCamIndex : 0,
                          dropdownColor: const Color(0xFF0F172A),
                          items: cameras.isEmpty
                              ? [
                                  const DropdownMenuItem(
                                    value: 0,
                                    child: Text("Simulated Mock Sensor", style: TextStyle(color: Colors.white, fontSize: 12)),
                                  )
                                ]
                              : List.generate(
                                  cameras.length,
                                  (index) {
                                    final cam = cameras[index];
                                    final label = "${cam.name} (${cam.lensDirection.name})";
                                    return DropdownMenuItem(
                                      value: index,
                                      child: Text(
                                        label,
                                        style: const TextStyle(color: Colors.white, fontSize: 12),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    );
                                  },
                                ),
                          onChanged: _isSwitchingCamera
                              ? null
                              : (val) {
                                  if (val != null) {
                                    _changeCamera(val, _selectedPreset);
                                  }
                                },
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 12),

              // Resolution Preset Selector
              Expanded(
                flex: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Resolution Preset",
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF334155)),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<ResolutionPreset>(
                          isExpanded: true,
                          value: _selectedPreset,
                          dropdownColor: const Color(0xFF0F172A),
                          items: const [
                            DropdownMenuItem(
                              value: ResolutionPreset.low,
                              child: Text("480p (Low)", style: TextStyle(color: Colors.white, fontSize: 12)),
                            ),
                            DropdownMenuItem(
                              value: ResolutionPreset.medium,
                              child: Text("720p (Optimal)", style: TextStyle(color: Colors.white, fontSize: 12)),
                            ),
                            DropdownMenuItem(
                              value: ResolutionPreset.high,
                              child: Text("1080p (High)", style: TextStyle(color: Colors.white, fontSize: 12)),
                            ),
                          ],
                          onChanged: _isSwitchingCamera
                              ? null
                              : (val) {
                                  if (val != null) {
                                    _changeCamera(_selectedCamIndex, val);
                                  }
                                },
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          if (_isSwitchingCamera) ...[
            const SizedBox(height: 10),
            const Row(
              children: [
                SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF38BDF8))),
                SizedBox(width: 8),
                Text("Re-negotiating camera stream pipeline...", style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11)),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHudToggleCard() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Live Device Telemetry HUD Overlay",
                style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 2),
              Text(
                "Display FPS, inference latency, and memory metrics in active viewport",
                style: TextStyle(color: Color(0xFF64748B), fontSize: 10.5),
              ),
            ],
          ),
          Switch(
            value: widget.isHudVisible,
            activeColor: const Color(0xFF38BDF8),
            onChanged: (val) => widget.onToggleHud(val),
          ),
        ],
      ),
    );
  }

  Future<void> _changeCamera(int cameraIndex, ResolutionPreset preset) async {
    setState(() {
      _isSwitchingCamera = true;
    });

    try {
      await widget.cameraService.switchCamera(cameraIndex, preset);
      _selectedCamIndex = cameraIndex;
      _selectedPreset = preset;

      final resName = preset == ResolutionPreset.low
          ? "640x480 (480p)"
          : preset == ResolutionPreset.medium
              ? "1280x720 (720p)"
              : "1920x1080 (1080p)";
      TelemetryService().setCameraResolution(resName);
    } catch (e) {
      TelemetryService().logError("Camera", "Failed to switch camera: $e");
    } finally {
      if (mounted) {
        setState(() {
          _isSwitchingCamera = false;
        });
      }
    }
  }
}
