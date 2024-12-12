document.addEventListener("DOMContentLoaded", function() {
    const buttonBACK = document.getElementById("buttonBACK");
    const button1 = document.getElementById("button1");
    const button2 = document.getElementById("button2");
    const button3 = document.getElementById("button3");
    const button4 = document.getElementById("button4");
    const button5 = document.getElementById("button5");

    if (buttonBACK) {
        buttonBACK.addEventListener("click", function() {
            window.location.href = "../index.html"; // Путь к index.html
        });
    }

    if (button1) {
        button1.addEventListener("click", function() {
            window.location.href = "podsite/puzzles.html"; 
        });
    }

    if (button2) {
        button2.addEventListener("click", function() {
            window.location.href = "podsite/play.html";
        });
    }

    if (button3) {
        button3.addEventListener("click", function() {
            window.location.href = "../tasks/task1.html"; 
        });
    }

    if (button4) {
        button4.addEventListener("click", function() {
            window.location.href = "../tasks/task2.html"; 
        });
    }

    if (button5) {
        button5.addEventListener("click", function() {
            window.location.href = "../tasks/task3.html"; 
        });
    }
});