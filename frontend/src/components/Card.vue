<template>
    <div :class="rootClasses">
        <div v-if="$slots.header" class="ui-card__header">
            <slot name="header" />
        </div>
        <div v-if="$slots.tab" class="ui-card__tab">
            <slot name="tab" />
        </div>
        <div v-if="$slots.subtitle" class="ui-card__subtitle">
            <slot name="subtitle" />
        </div>
        <div class="ui-card__body">
            <slot />
        </div>
    </div>
</template>

<script>
    export default{
        name: "Card",
        props: {
            variant: {
                type: String,
                default: "default",
                validator(value) {
                    return ["default", "job", "minimal"].includes(value)
                }
            }
        },
        computed: {
            rootClasses() {
                return ["ui-card", `ui-card--${this.variant}`]
            }
        }
    }
</script>

<style src="./css/Card.css"></style>
