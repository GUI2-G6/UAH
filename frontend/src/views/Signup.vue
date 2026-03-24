<template>
    <div class="page">
        <h1>Signup</h1>
            <p>Track every application in one place</p>
            <input type="email" v-model="email" placeholder="Enter Your Email to Begin account" />
            <button @click="singup">Submit</button>
            <div class="signup-row">
            <span>Already have an account? </span>
            <a @click.prevent="login" href="#">Return to Login Page</a>
            </div>
        </div>
</template>


<script>
    export default{
        name: "Signup"
    }
</script>

<style src="./css/Login.css"></style>