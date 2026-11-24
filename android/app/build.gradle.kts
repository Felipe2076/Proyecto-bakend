plugins { id("com.android.application") }
val production = "https://54.205.69.94"
val testUrl = providers.gradleProperty("sigedTestUrl").orElse(production)
android {
    namespace = "cl.laserena.siged.movil"
    compileSdk { version = release(37) }
    defaultConfig {
        applicationId = "cl.laserena.siged.movil"
        minSdk = 26
        targetSdk = 37
        versionCode = 2
        versionName = "2.0.0"
        buildConfigField("String", "BASE_URL", "\"$production\"")
        buildConfigField("String", "TEST_HOST", "\"10.0.2.2\"")
    }
    buildFeatures { buildConfig = true }
    buildTypes {
        debug {
            buildConfigField("String", "BASE_URL", "\"${testUrl.get()}\"")
            buildConfigField("String", "TEST_HOST", "\"${testUrl.get().substringAfter("://").substringBefore("/").substringBefore(":")}\"")
        }
        release { isMinifyEnabled = false }
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies {
    implementation("androidx.activity:activity-ktx:1.8.0")
    implementation("androidx.core:core-ktx:1.10.1")
    // Animaciones de carga, éxito y lista vacía (JSON en res/raw).
    implementation("com.airbnb.android:lottie:6.4.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
}
