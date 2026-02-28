package com.doppelganger.app.data.api.models

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val username: String,
    val password: String
)

data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String? = null
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("user_id") val userId: String,
    val username: String
)

data class FaceMatch(
    @SerializedName("face_id") val faceId: String,
    val year: Int?,
    val school: String?,
    @SerializedName("yearbook_url") val yearbookUrl: String,
    @SerializedName("page_url") val pageUrl: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("similarity_score") val similarityScore: Float
)

data class CompareResponse(
    @SerializedName("total_compared") val totalCompared: Int,
    val results: List<FaceMatch>
)

data class StatsResponse(
    @SerializedName("total_faces") val totalFaces: Int,
    @SerializedName("total_yearbooks") val totalYearbooks: Int,
    @SerializedName("user_favorites") val userFavorites: Int
)

data class FavoritesResponse(
    val favorites: List<FaceMatch>
)

data class ScraperStatus(
    @SerializedName("total_yearbooks") val totalYearbooks: Int,
    @SerializedName("total_faces") val totalFaces: Int,
    val processing: Int,
    val completed: Int,
    val queued: Int,
    val failed: Int
)

data class ApiResponse(
    val success: Boolean,
    val message: String
)