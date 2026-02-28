package com.doppelganger.app.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_prefs")

@Singleton
class TokenManager @Inject constructor(
    private val context: Context
) {
    private val dataStore = context.dataStore
    
    companion object {
        private val TOKEN_KEY = stringPreferencesKey("auth_token")
        private val USER_ID_KEY = stringPreferencesKey("user_id")
        private val USERNAME_KEY = stringPreferencesKey("username")
    }
    
    suspend fun saveToken(token: String, userId: String, username: String) {
        dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[USER_ID_KEY] = userId
            prefs[USERNAME_KEY] = username
        }
    }
    
    suspend fun clearToken() {
        dataStore.edit { prefs ->
            prefs.clear()
        }
    }
    
    fun getToken(): Flow<String?> = dataStore.data.map { prefs ->
        prefs[TOKEN_KEY]
    }
    
    fun getUserId(): Flow<String?> = dataStore.data.map { prefs ->
        prefs[USER_ID_KEY]
    }
    
    fun getUsername(): Flow<String?> = dataStore.data.map { prefs ->
        prefs[USERNAME_KEY]
    }
}