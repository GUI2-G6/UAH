<template>
    <div class="card">
        <div v-if="$slots.header" class="header">
            <slot name="header" />
        </div>
        <div v-if="$slots.tab" class="tab">
            <slot name="tab" />
        </div>
        <div v-if="$slots.subtitle" class="subtitle">
            <slot name="subtitle" />
        </div>
        <div class="body">
            <slot />
        </div>
    </div>
</template>

<script>
    export default{
        name: "Card"
    }
</script>

<style src="./css/Card.css"></style>