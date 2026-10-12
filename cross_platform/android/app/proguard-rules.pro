# -----------------------------------------------------------------------------
# ProGuard / R8 Rules for Gesture Studio Pro (MediaPipe Tasks & TFLite)
# -----------------------------------------------------------------------------

# Keep MediaPipe Tasks Vision & Core JNI bindings
-keep class com.google.mediapipe.tasks.** { *; }
-keep class com.google.mediapipe.framework.** { *; }
-keep interface com.google.mediapipe.** { *; }
-dontwarn com.google.mediapipe.**

# Keep TensorFlow Lite and GPU/NNAPI Delegate JNI symbols
-keep class org.tensorflow.lite.** { *; }
-keep class org.tensorflow.lite.gpu.** { *; }
-keep class org.tensorflow.lite.nnapi.** { *; }
-dontwarn org.tensorflow.lite.**

# Keep AndroidX CameraX Lifecycle and Capture pipelines
-keep class androidx.camera.** { *; }
-dontwarn androidx.camera.**

# Keep Native JNI function signatures
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep Flutter Platform Channel models and DTOs
-keep class com.gesturestudio.pro.** { *; }
