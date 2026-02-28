package com.doppelganger.app.data.api

import com.doppelganger.app.data.api.models.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    
    // Authentication
    @POST("api/mobile/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<TokenResponse>
    
    @POST("api/mobile/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>
    
    // Face Comparison
    @Multipart
    @POST("api/mobile/compare")
    suspend fun compareImage(
        @Part file: MultipartBody.Part,
        @Part("limit") limit: RequestBody,
        @Header("Authorization") token: String? = null
    ): Response<CompareResponse>
    
    // Favorites
    @POST("api/mobile/favorites")
    suspend fun addFavorite(
        @Body faceId: Map<String, String>,
        @Query("token") token: String
    ): Response<ApiResponse>
    
    @DELETE("api/mobile/favorites/{face_id}")
    suspend fun removeFavorite(
        @Path("face_id") faceId: String,
        @Query("token") token: String
    ): Response<ApiResponse>
    
    @GET("api/mobile/favorites")
    suspend fun getFavorites(
        @Query("token") token: String
    ): Response<FavoritesResponse>
    
    // Stats
    @GET("api/mobile/stats")
    suspend fun getStats(
        @Query("token") token: String? = null
    ): Response<StatsResponse>
    
    // Admin
    @GET("api/mobile/admin/scraper-status")
    suspend fun getScraperStatus(
        @Query("token") token: String
    ): Response<ScraperStatus>
    
    @POST("api/mobile/admin/start-scraping")
    suspend fun startScraping(
        @Query("identifier") identifier: String,
        @Query("max_pages") maxPages: Int,
        @Query("token") token: String
    ): Response<ApiResponse>
    
    @POST("api/mobile/admin/auto-discover")
    suspend fun autoDiscover(
        @Query("limit") limit: Int,
        @Query("token") token: String
    ): Response<ApiResponse>
}