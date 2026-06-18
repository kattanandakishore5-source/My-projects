/**
 * main.js — Vanilla JS replacement for HTMX
 * Handles Add to Cart, Quantity Updates, and Wishlist Toggles
 * via fetch() API with JSON responses from Django views.
 */

(function () {
    'use strict';

    // ─── CSRF Token ────────────────────────────────────────────────
    function getCSRFToken() {
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        if (cookie) return cookie.split('=')[1];
        // Fallback: read from a hidden input
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    // ─── Helpers ───────────────────────────────────────────────────
    function updateCartBadge(count) {
        document.querySelectorAll('#cart_count, .cart-badge').forEach(el => {
            el.textContent = count;
        });
    }

    /** Build quantity control HTML (card-style) */
    function buildQtyControlsCard(productId, qty) {
        return `
            <div class="quantity-controls mb-2">
                <button class="btn-qty" data-product-id="${productId}" data-action="decrement" aria-label="Decrease quantity">&minus;</button>
                <span class="font-weight-bold text-white qty-display">${qty}</span>
                <button class="btn-qty" data-product-id="${productId}" data-action="increment" aria-label="Increase quantity">+</button>
            </div>
            <div class="d-flex w-100 mt-2" style="gap: 8px;">
                <a href="/shop/products/${productId}" class="w-100" style="flex: 1;">
                    <button type="button" class="btn btn-secondary w-100">View</button>
                </a>
            </div>`;
    }

    /** Build "Add to Cart" button HTML (card-style) */
    function buildAddButtonCard(productId) {
        return `
            <button class="btn btn-primary w-100 btn-add-cart mb-2" data-product-id="${productId}">Add To Cart</button>
            <div class="d-flex w-100 mt-2" style="gap: 8px;">
                <a href="/shop/products/${productId}" class="w-100" style="flex: 1;">
                    <button type="button" class="btn btn-secondary w-100">View</button>
                </a>
            </div>`;
    }

    /** Build quantity selector for product detail page */
    function buildQtyControlsDetail(productId, qty) {
        return `
            <div class="qty-selector mb-3">
                <button class="btn-qty-detail" data-product-id="${productId}" data-action="decrement" aria-label="Decrease quantity">&minus;</button>
                <span class="qty-value qty-display">${qty}</span>
                <button class="btn-qty-detail" data-product-id="${productId}" data-action="increment" aria-label="Increase quantity">+</button>
            </div>`;
    }

    // ─── POST helper ───────────────────────────────────────────────
    async function postJSON(url) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
        return resp.json();
    }

    // ─── Add to Cart (card buttons) ────────────────────────────────
    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.btn-add-cart');
        if (!btn) return;
        e.preventDefault();

        const productId = btn.dataset.productId;
        if (!productId) return;

        // Loading state
        const origText = btn.textContent;
        btn.disabled = true;
        btn.innerHTML = 'Adding...<span class="spinner-btn"></span>';

        try {
            const data = await postJSON(`/shop/add-to-cart/${productId}/`);
            updateCartBadge(data.cart_count);

            // Replace button area with quantity controls
            const cartAction = btn.closest('.cart-action');
            if (cartAction) {
                cartAction.innerHTML = buildQtyControlsCard(productId, data.cart_qty);
            }

            if (typeof showToast === 'function') {
                showToast(data.message || 'Added to cart', 'success');
            }
        } catch (err) {
            console.error('Add to cart failed:', err);
            btn.disabled = false;
            btn.textContent = origText;
            if (typeof showToast === 'function') {
                showToast('Failed to add to cart', 'error');
            }
        }
    });

    // ─── Add to Cart (product detail page hero button) ─────────────
    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.btn-add-cart-hero');
        if (!btn) return;
        e.preventDefault();

        // Prevent adding again if the item is already in the cart
        if (btn.classList.contains('in-cart')) {
            return;
        }

        const productId = btn.dataset.productId;
        if (!productId) return;

        btn.disabled = true;
        btn.innerHTML = 'Adding...<span class="spinner-btn"></span>';

        try {
            const data = await postJSON(`/shop/add-to-cart/${productId}/`);
            updateCartBadge(data.cart_count);

            // Show quantity selector in the action center
            const qtyContainer = document.getElementById('detail-qty-container');
            if (qtyContainer) {
                qtyContainer.innerHTML = buildQtyControlsDetail(productId, data.cart_qty);
                qtyContainer.style.display = 'block';
            }
            btn.textContent = '✓ In Cart';
            btn.classList.add('in-cart');
            btn.disabled = false;

            if (typeof showToast === 'function') {
                showToast(data.message || 'Added to cart', 'success');
            }
        } catch (err) {
            console.error('Add to cart failed:', err);
            btn.disabled = false;
            btn.textContent = 'Add To Cart';
            if (typeof showToast === 'function') {
                showToast('Failed to add to cart', 'error');
            }
        }
    });

    // ─── Quantity Update (card-style ± buttons) ────────────────────
    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.btn-qty');
        if (!btn) return;
        e.preventDefault();

        const productId = btn.dataset.productId;
        const action = btn.dataset.action;
        if (!productId || !action) return;

        btn.disabled = true;

        try {
            const data = await postJSON(`/shop/update-cart/${productId}/${action}/`);
            updateCartBadge(data.cart_count);

            const cartAction = btn.closest('.cart-action');
            if (!cartAction) return;

            if (data.cart_qty <= 0) {
                // Item removed — show Add to Cart button again
                cartAction.innerHTML = buildAddButtonCard(productId);
            } else {
                cartAction.innerHTML = buildQtyControlsCard(productId, data.cart_qty);
            }

            if (typeof showToast === 'function') {
                showToast(data.message || 'Cart updated', 'success');
            }
        } catch (err) {
            console.error('Update cart failed:', err);
            btn.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Failed to update cart', 'error');
            }
        }
    });

    // ─── Quantity Update (product detail page ± buttons) ───────────
    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.btn-qty-detail');
        if (!btn) return;
        e.preventDefault();

        const productId = btn.dataset.productId;
        const action = btn.dataset.action;
        if (!productId || !action) return;

        btn.disabled = true;

        try {
            const data = await postJSON(`/shop/update-cart/${productId}/${action}/`);
            updateCartBadge(data.cart_count);

            const qtyContainer = document.getElementById('detail-qty-container');
            const heroBtn = document.querySelector('.btn-add-cart-hero');

            if (data.cart_qty <= 0) {
                // Item removed
                if (qtyContainer) {
                    qtyContainer.innerHTML = '';
                    qtyContainer.style.display = 'none';
                }
                if (heroBtn) {
                    heroBtn.textContent = 'Add To Cart';
                    heroBtn.classList.remove('in-cart');
                    heroBtn.disabled = false;
                }
            } else {
                if (qtyContainer) {
                    qtyContainer.innerHTML = buildQtyControlsDetail(productId, data.cart_qty);
                }
                if (heroBtn) {
                    heroBtn.textContent = '✓ In Cart';
                    heroBtn.classList.add('in-cart');
                }
            }

            if (typeof showToast === 'function') {
                showToast(data.message || 'Cart updated', 'success');
            }
        } catch (err) {
            console.error('Update cart failed:', err);
            btn.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Failed to update cart', 'error');
            }
        }
    });

    // ─── Wishlist Toggle ───────────────────────────────────────────
    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.btn-wishlist');
        if (!btn) return;
        e.preventDefault();

        const productId = btn.dataset.productId;
        if (!productId) return;

        btn.disabled = true;

        try {
            const data = await postJSON(`/shop/toggle-wishlist/${productId}/`);

            if (data.in_wishlist) {
                btn.classList.add('active');
                btn.textContent = '♥';
            } else {
                btn.classList.remove('active');
                btn.textContent = '♡';
            }

            if (typeof showToast === 'function') {
                showToast(data.message || 'Wishlist updated', 'success');
            }
        } catch (err) {
            console.error('Wishlist toggle failed:', err);
            if (typeof showToast === 'function') {
                showToast('Failed to update wishlist', 'error');
            }
        } finally {
            btn.disabled = false;
        }
    });

    // ─── Interactive Star Rating (Review Form) ─────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        const starContainer = document.querySelector('.star-rating-input');
        if (!starContainer) return;

        const radios = starContainer.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', function () {
                // The hidden original input keeps in sync
                const hiddenInput = document.getElementById('id_rating');
                if (hiddenInput) {
                    hiddenInput.value = this.value;
                }
            });
        });
    });

    // ─── Category Pill Filtering ───────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        const pills = document.querySelectorAll('.category-pill[data-category]');
        if (!pills.length) return;

        pills.forEach(pill => {
            pill.addEventListener('click', function (e) {
                e.preventDefault();

                // Toggle active state
                pills.forEach(p => p.classList.remove('active'));
                this.classList.add('active');

                const cat = this.dataset.category;
                const sections = document.querySelectorAll('.category-section');

                sections.forEach(section => {
                    if (cat === 'all' || section.dataset.category === cat) {
                        section.style.display = '';
                    } else {
                        section.style.display = 'none';
                    }
                });
            });
        });
    });

})();
