// shop/static/shop/js/tracker.js
$('#trackerForm').submit(function (event) {
    event.preventDefault();
    $('#items').empty();

    const formData = {
        'orderId': $('input[name=orderId]').val(),
        'email': $('input[name=email]').val(),
        'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val()
    };

    $.ajax({
        type: 'POST',
        url: '/shop/tracker/',
        data: formData,
        encode: true
    })
    .done(function (data) {
        $('#citems').empty();
        let data_received = JSON.parse(data);

        if (data_received['status'] === 'success') {
            // Fixed: Added missing 'let' to prevent global variable leakage
            let updates = data_received['updates'];
            for (let i = 0; i < updates.length; i++) {
                let text = updates[i]['text'];
                let time = updates[i]['time'];
                let mystr = `<li class="store-list-item d-flex justify-content-between align-items-center bg-transparent border-0 px-0">
                <span class="text-primary">${text}</span>
                <span class="badge badge-count badge-pill">${time}</span>
            </li>`;
                $('#items').append(mystr);
            }

            // Fixed: Added missing 'let' to prevent global variable leakage
            let cart = JSON.parse(data_received['itemsJson']);
            for (let item in cart) {
                let name = cart[item][1];
                let qty = cart[item][0];
                let mystr = `<li class="store-list-item d-flex justify-content-between align-items-center bg-transparent border-0 px-0">
                ${name}
                <span class="badge badge-count badge-pill">${qty}</span>
            </li>`;
                $('#citems').append(mystr);
            }
        } else {
            let mystr = `<li class="store-list-item d-flex justify-content-between align-items-center border-0 px-0 text-secondary">
                Sorry, We are not able to fetch this order id and email. Make sure to type correct order Id and email</li>`;
            $('#items').append(mystr);
            $('#citems').append(mystr);
        }
    })
    .fail(function() {
        // Optimized: Added fail block for proper error handling
        let mystr = `<li class="store-list-item d-flex justify-content-between align-items-center border-0 px-0 text-danger">
            A server error occurred. Please try again later.</li>`;
        $('#items').append(mystr);
        $('#citems').append(mystr);
    });
});