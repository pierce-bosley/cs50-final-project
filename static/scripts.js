function reset_pattern_dropdown() {
    document.getElementById("patternDropdown").innerHTML = "Select Pattern";
    document.getElementById("monthly").hidden = true;
    document.getElementById("weekly").hidden = true;
    switch_date_picker(document.getElementById("start-date-cal"), "date");
}

function switch_date_picker(date_picker, format) {
    date_picker.value = "";
    date_picker.type = format;
    document.getElementById("dependent-submit").disabled = true;
};

function pattern_selection(pattern) {
    document.getElementById("patternDropdown").innerHTML = pattern.innerHTML;
    document.getElementById("monthly").hidden = true;
    document.getElementById("weekly").hidden = true;
    document.getElementById("leap-year").hidden = true;
    document.getElementById("monthly-pattern-warning").hidden = true;
    switch (pattern.value) {
        case "yearly": {
            switch_date_picker(document.getElementById("start-date-cal"), "date");
            document.getElementById("selected-pattern").value = pattern.value;
            document.getElementById("start-date").hidden = false;
            if (document.getElementById("start-date").value) {
                if (document.getElementById("start-date").value.slice(5) === "02-29") {
                    document.getElementById("leap-year").hidden = false;
                }
            }
            break;
        }
        case "monthly": {
            let day_selects = document.getElementsByClassName("monthly-pattern");
            for (let i = 0; i < day_selects.length; i++) {
                if (day_selects[i].value === "1") {
                    if (!day_selects[i].parentElement.classList.contains("active")) {
                        day_selects[i].parentElement.classList.add("active");
                    }
                } else {
                    if (day_selects[i].parentElement.classList.contains("active")) {
                        day_selects[i].parentElement.classList.remove("active");
                    }
                }
            }
            switch_date_picker(document.getElementById("start-date-cal"), "month");
            document.getElementById("selected-pattern").value = pattern.value;
            document.getElementById("start-date").hidden = false;
            document.getElementById(pattern.value).hidden = false;
            break;
        }
        case "weekly": {
            let weekly_selects = document.getElementsByClassName("weekly-pattern");
            for (let i = 0; i < weekly_selects.length; i++) {
                if (weekly_selects[i].value === "1") {
                    if (!weekly_selects[i].parentElement.classList.contains("active")) {
                        weekly_selects[i].parentElement.classList.add("active");
                    }
                } else {
                    if (weekly_selects[i].parentElement.classList.contains("active")) {
                        weekly_selects[i].parentElement.classList.remove("active");
                    }
                }
            }
            switch_date_picker(document.getElementById("start-date-cal"), "date");
            document.getElementById("start-date").hidden = false;
            document.getElementById(pattern.value).hidden = false;
            document.getElementById("selected-pattern").value = pattern.value;
            break;
        }
        case "daily": {
            switch_date_picker(document.getElementById("start-date-cal"), "date");
            document.getElementById("start-date").hidden = false;
            document.getElementById("selected-pattern").value = pattern.value;
            break;
        }
    }
}

function check_submit_reqs(required) {
    let submit = document.getElementById("dependent-submit");
    let matching = document.getElementsByClassName("match");
    for (let i = 0; i < required.length; i++) {
        if (matching.length > 0) {
            let match = matching[0].value;
            if ((required[i].classList.contains("match")) && (required[i].value != match)) {
                submit.disabled = true;
                return;
            }
        }
        if (required[i].value === "") {
            submit.disabled = true;
            return;
        }
    }
    submit.disabled = false;
    return;
}

function selected_day_warning(date_picker) {
    if (document.getElementById("selected-pattern").value === "yearly" && date_picker.value.slice(5) === "02-29") {
        document.getElementById("leap-year").hidden = false;
    }
    if (document.getElementById("selected-pattern").value === "monthly") {
        switch (date_picker.value.slice(8)) {
            case "29":
            case "30":
            case "31":
                document.getElementById("monthly-pattern-warning").hidden = false;
                break;
            default:
                document.getElementById("monthly-pattern-warning").hidden = true;
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    let required = document.getElementsByClassName("required");
    for (let i = 0; i < required.length; i++) {
        required[i].onchange = function() {
            check_submit_reqs(required);
            if (required[i].id === "start-date-cal") {
                selected_day_warning(this);
            }
        };
        required[i].onkeyup = function() {
            check_submit_reqs(required);
        };
    }
    let patterns = document.getElementsByClassName("pattern");
    for (let i = 0; i < patterns.length; i++) {
        patterns[i].onclick = function() {
            pattern_selection(patterns[i]);
        };
    }
    let monthly = document.getElementsByClassName("monthly-pattern");
    for (let i = 0; i < monthly.length; i++) {
        if (monthly[i].value != "3") {
            monthly[i].onchange = function() {
                switch_date_picker(document.getElementById("start-date-cal"), "month");
                document.getElementById("monthly-pattern-warning").hidden = true;
            };
        } else {
            monthly[i].onchange = function() {
                switch_date_picker(document.getElementById("start-date-cal"), "date");
            };
        }
    }
    if (document.getElementById("new-savings")) {
        document.getElementById("new-savings").onchange = function() {
            document.getElementById("debit").innerHTML = "withdrawal";
            document.getElementById("credit").innerHTML = "Deposit";
        };
        document.getElementById("new-spending").onchange = function() {
            document.getElementById("debit").innerHTML = "Debit";
            document.getElementById("credit").innerHTML = "Credit";
        };
    }
    let frequency = document.getElementsByClassName("frequency");
    for (let i = 0; i < frequency.length; i++) {
        if (frequency[i].value === "single") {
            frequency[i].onchange = function() {
                reset_pattern_dropdown();
                document.getElementById("patternDropdown").hidden = true;
                document.getElementById("leap-year").hidden = true;
                document.getElementById("start-date").children[0].innerHTML = "Date";
                document.getElementById("start-date").hidden = false;
            };
        }
        if (frequency[i].value === "recurring") {
            frequency[i].onchange = function() {
                reset_pattern_dropdown();
                document.getElementById("patternDropdown").hidden = false;
                document.getElementById("start-date").children[0].innerHTML = "Start Date";
                document.getElementById("start-date").hidden = true;
            };
        }
    }
    let deletes = document.getElementsByName("delete")
    for (let i = 0; i < deletes.length; i++) {
        deletes[i].onchange = function() {
            if (this.parentElement.classList.contains("active")) {
                console.log("test1")
                this.parentElement.children[1].innerHTML = "&nbsp;";
            } else {
                console.log("test2")
                this.parentElement.children[1].innerHTML = "X";
            }
        };
    }
});