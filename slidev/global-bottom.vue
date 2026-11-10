<template>
  <div
    v-if="$slidev.nav.currentPage > 1 && $slidev.nav.currentPage < $slidev.nav.total"
    class="deck-footer"
  >
    <span class="deck-footer__brand">
      <i class="deck-footer__mark" />
      La borne qui écoute
      <span class="deck-footer__team">Équipe 5</span>
    </span>

    <nav class="deck-footer__stages">
      <span
        v-for="(label, index) in stages"
        :key="label"
        :class="{ active: $slidev.nav.currentPage === index + 2 }"
      >
        {{ label }}
      </span>
    </nav>

    <span class="deck-footer__meta">
      <span class="deck-footer__date">10 nov. 2026</span>
      <span class="deck-footer__page">
        {{ String($slidev.nav.currentPage).padStart(2, '0') }} / {{ String($slidev.nav.total).padStart(2, '0') }}
      </span>
    </span>
  </div>
</template>

<script setup>
const stages = ['Contexte', 'Concept', 'Données', 'Démo', 'Économie']
</script>
