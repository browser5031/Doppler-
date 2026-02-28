package com.doppelganger.app.data.repository

import com.doppelganger.app.data.api.ApiService
import com.doppelganger.app.data.api.models.*
import com.doppelganger.app.data.local.TokenManager
import kotlinx.coroutines.flow.first
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DoppelgangerRepository @Inject constructor(
    private val apiService: ApiService,
    private val tokenManager: TokenManager
) {
    
    // Auth
    suspend fun register(username: String, password: String, email: String?): Result<TokenResponse> {
        return try {
            val response = apiService.register(RegisterRequest(username, password, email))
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!
                tokenManager.saveToken(tokenResponse.accessToken, tokenResponse.userId, tokenResponse.username)
                Result.success(tokenResponse)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun login(username: String, password: String): Result<TokenResponse> {
        return try {
            val response = apiService.login(LoginRequest(username, password))
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!
                tokenManager.saveToken(tokenResponse.accessToken, tokenResponse.userId, tokenResponse.username)
                Result.success(tokenResponse)
            } else {
                Result.failure(Exception("Invalid credentials"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun logout() {
        tokenManager.clearToken()
    }
    
    fun getToken() = tokenManager.getToken()
    fun getUsername() = tokenManager.getUsername()
    
    // Face Comparison
    suspend fun compareImage(imageFile: File, limit: Int = 50): Result<CompareResponse> {
        return try {
            val token = tokenManager.getToken().first()
            val requestFile = imageFile.asRequestBody("image/*".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", imageFile.name, requestFile)
            val limitBody = limit.toString().toRequestBody("text/plain".toMediaTypeOrNull())
            
            val response = apiService.compareImage(body, limitBody, token?.let { "Bearer $it" })
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Favorites
    suspend fun addFavorite(faceId: String): Result<Boolean> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.addFavorite(mapOf("face_id" to faceId), token)
            if (response.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun removeFavorite(faceId: String): Result<Boolean> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.removeFavorite(faceId, token)
            if (response.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getFavorites(): Result<List<FaceMatch>> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.getFavorites(token)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.favorites)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Stats
    suspend fun getStats(): Result<StatsResponse> {
        return try {
            val token = tokenManager.getToken().first()
            val response = apiService.getStats(token)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Admin
    suspend fun getScraperStatus(): Result<ScraperStatus> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.getScraperStatus(token)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun startScraping(identifier: String, maxPages: Int): Result<Boolean> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.startScraping(identifier, maxPages, token)
            if (response.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun autoDiscover(limit: Int): Result<Boolean> {
        return try {
            val token = tokenManager.getToken().first() ?: return Result.failure(Exception("Not logged in"))
            val response = apiService.autoDiscover(limit, token)
            if (response.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception(response.message()))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}