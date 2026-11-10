<template>
  <div
    v-if="$slidev.nav.currentPage > 1"
    class="deck-progress"
    aria-hidden="true"
  >
    <span :style="{ width: ($slidev.nav.currentPage / $slidev.nav.total) * 100 + '%' }" />
  </div>
</template>
