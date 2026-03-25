// shop/static/shop/js/tracker.js

$('#trackerForm').submit(function (event) {
    $('#items').empty();
    var formData = {
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
            if (data_received['status'] == 'success') {
                updates = data_received['updates'];
                for (i = 0; i < updates.length; i++) {
                    let text = updates[i]['text'];
                    let time = updates[i]['time'];
                    let mystr = `<li class="store-list-item d-flex justify-content-between align-items-center bg-transparent border-0 px-0">
                    <span class="text-primary">${text}</span>
                    <span class="badge badge-count badge-pill">${time}</span>
                </li>`;
                    $('#items').append(mystr);
                }

                // Fill in the order details
                cart = JSON.parse(data_received['itemsJson']);
                for (item in cart) {
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
        });
    event.preventDefault();
});
