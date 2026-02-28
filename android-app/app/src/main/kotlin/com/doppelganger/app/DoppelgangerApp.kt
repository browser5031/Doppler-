package com.doppelganger.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class DoppelgangerApp : Application() {
    override fun onCreate() {
        super.onCreate()
    }
}