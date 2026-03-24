<template>
    <div class="page">
        <h1>Login</h1>
            <p>Track every application in one place</p>
            <input type="email" v-model="email" placeholder="Enter Your Email to Begin Logon" />
            <button @click="login">Submit</button>
            <div class="signup-row">
            <span>Don't have an account? </span>
            <a @click.prevent="signup" href="#">Create an account</a>
            </div>
        </div>
</template>


<script>
    export default{
        name: "Login"
    }
</script>

<style src="./css/Login.css"></style>