// shop/static/shop/js/checkout.js
document.addEventListener('DOMContentLoaded', function () {
    const itemsList = document.getElementById('items');
    const itemsJsonField = document.getElementById('itemsJson');

    if (itemsList && itemsJsonField) {
        const cartItems = {};
        const listItems = itemsList.querySelectorAll('li');

        listItems.forEach(function (li) {
            const nameEl = li.childNodes[0];
            const badgeEl = li.querySelector('.badge');
            if (nameEl && badgeEl) {
                const name = nameEl.textContent.trim();
                const qty = parseInt(badgeEl.textContent.trim(), 10) || 0;
                if (name && qty > 0) {
                    cartItems[name] = [qty, name];
                }
            }
        });

        itemsJsonField.value = JSON.stringify(cartItems);
    }
});