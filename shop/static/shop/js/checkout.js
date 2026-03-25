// shop/static/shop/js/checkout.js

// Build itemsJson from the server-rendered cart items for form submission
document.addEventListener('DOMContentLoaded', function () {
    var itemsList = document.getElementById('items');
    var itemsJsonField = document.getElementById('itemsJson');

    if (itemsList && itemsJsonField) {
        var cartItems = {};
        var listItems = itemsList.querySelectorAll('li');

        listItems.forEach(function (li) {
            var nameEl = li.childNodes[0];
            var badgeEl = li.querySelector('.badge');
            if (nameEl && badgeEl) {
                var name = nameEl.textContent.trim();
                var qty = parseInt(badgeEl.textContent.trim(), 10) || 0;
                if (name && qty > 0) {
                    cartItems[name] = [qty, name];
                }
            }
        });

        itemsJsonField.value = JSON.stringify(cartItems);
    }
});
