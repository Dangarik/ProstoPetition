<script setup>
import { RouterLink } from 'vue-router'
import { dateLabel, excerpt, statusLabel } from '../format.js'
defineProps({ petition: { type: Object, required: true } })
</script>

<template>
  <article class="petition-card card h-100 border-0">
    <div class="card-body d-flex flex-column">
      <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
        <span class="category-pill">{{ petition.category_name }}</span>
        <span class="status-pill" :class="'status-' + petition.status">{{ statusLabel(petition.status) }}</span>
      </div>
      <h3 class="h5 card-title"><RouterLink :to="{ name: 'petition', params: { id: petition.id } }">{{ petition.title }}</RouterLink></h3>
      <p class="card-text text-secondary flex-grow-1">{{ excerpt(petition.text) }}</p>
      <div class="card-meta d-flex flex-wrap gap-2 justify-content-between">
        <span>Автор: <strong>{{ petition.author }}</strong></span>
        <span>{{ dateLabel(petition.created_at) }}</span>
      </div>
      <div class="card-bottom d-flex align-items-center justify-content-between mt-3 pt-3">
        <span class="vote-count"><strong>{{ petition.vote_count }}</strong><span v-if="petition.vote_threshold"> / {{ petition.vote_threshold }}</span> голосів</span>
        <RouterLink class="btn btn-outline-primary btn-sm" :to="{ name: 'petition', params: { id: petition.id } }">Переглянути</RouterLink>
      </div>
    </div>
  </article>
</template>

