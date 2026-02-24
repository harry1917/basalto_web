/* ===========================
   BASALTO Cart + Checkout
   (Wompi in new tab + WhatsApp for transfer)
=========================== */
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    // ✅ evita doble-binding si el script se carga dos veces
    if (window.__BASALTO_BOUND__) return;
    window.__BASALTO_BOUND__ = true;

    // ========= Config =========
    const SHIPPING_FLAT = 3.0;

    // ========= State =========
    const cart = [];
    let currentProduct = null;

    // ========= Helpers =========
    const $ = (id) => document.getElementById(id);

    const money = (n) => {
      const v = Number(n || 0);
      return `$${v.toFixed(2)}`;
    };

    // ✅ Normaliza precios tipo "30,00" / "$30.00" / "30" -> Number 30.00
    const normalizePrice = (val) => {
      let s = String(val ?? "").trim();
      s = s.replace(",", ".");
      s = s.replace(/[^0-9.]/g, "");
      const parts = s.split(".");
      if (parts.length > 2) s = parts[0] + "." + parts.slice(1).join("");
      const n = Number(s || 0);
      return Number.isFinite(n) ? n : 0;
    };

    const normalizeSizeKey = (s) => String(s || "").trim().toUpperCase();
    const isOneSize = (s) =>
      ["UNI", "UNICA", "ÚNICA", "ONE", "ONE SIZE", "OS", "U"].includes(normalizeSizeKey(s));

    const getAvailableSizes = (skuMap) => {
      const m = skuMap || {};
      return Object.keys(m).filter((k) => String(m[k] || "").trim());
    };

    // ✅ parse robusto de skuMap (soporta \" escapado)
    const parseSkuMap = (raw) => {
      const s = String(raw || "").trim();
      if (!s) return {};
      try {
        return JSON.parse(s);
      } catch (_) {
        try {
          return JSON.parse(s.replace(/\\"/g, '"'));
        } catch (e2) {
          console.log("SKU MAP PARSE ERROR (raw):", s.slice(0, 120), e2);
          return {};
        }
      }
    };

    // ✅ detección automática de tipo si no viene data-kind
    const inferKind = (kindFromDom, skuMap) => {
      const k = String(kindFromDom || "").trim().toLowerCase();
      if (k) return k;

      const sizes = getAvailableSizes(skuMap);
      const norm = sizes.map(normalizeSizeKey);

      if (norm.length <= 1) return "accessory";
      if (norm.some(isOneSize)) return "accessory";
      return "shirt";
    };

    const getItemUnitPrice = (it) => {
      const p = it.unit_price ?? it.price ?? 0;
      const num = Number(p);
      return Number.isFinite(num) ? num : 0;
    };

    const calcSubtotal = (items) => {
      return items.reduce((acc, it) => {
        const price = getItemUnitPrice(it);
        const qty = Number(it.qty || 1);
        return acc + price * (Number.isFinite(qty) ? qty : 1);
      }, 0);
    };

    // 🔑 Key única para merge (prioriza SKU si existe)
    const itemKey = (it) => {
      const sku = String(it.sku || "").trim();
      const size = String(it.size || "M").trim().toUpperCase();
      if (sku) return `SKU:${sku}|SIZE:${size}`;

      return [
        (it.title || "").trim(),
        (it.sleeve || "").trim(),
        (it.color || "").trim(),
        size,
        String(it.price ?? it.unit_price ?? ""),
        (it.img || "").trim(),
      ].join("|");
    };

    const addOrMerge = (item) => {
      const k = itemKey(item);
      const idx = cart.findIndex((x) => itemKey(x) === k);
      if (idx >= 0) {
        cart[idx].qty = Number(cart[idx].qty || 1) + Number(item.qty || 1);
      } else {
        cart.push(item);
      }
    };

    const resetBtn = (id) => {
      const el = $(id);
      if (!el || !el.parentNode) return null;
      const clone = el.cloneNode(true);
      el.parentNode.replaceChild(clone, el);
      return clone;
    };

    const openModalById = (id) => {
      const m = $(id);
      if (!m) return;
      m.classList.add("is-open");
      m.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    };

    const closeModalById = (id) => {
      const m = $(id);
      if (!m) return;
      if (m.contains(document.activeElement)) document.activeElement.blur();
      m.classList.remove("is-open");
      m.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    };

    // ========= Elements (Checkout Modal) =========
    const checkoutModal = $("checkoutModal");
    const checkoutForm = $("checkoutForm");
    const confirmOrderBtn = $("confirmOrderBtn");
    const transferBox = $("transferBox");
    const transferRefHint = $("transferRefHint");

    const coName = $("coName");
    const coPhone = $("coPhone");
    const coAddress1 = $("coAddress1");
    const coAddress2 = $("coAddress2");
    const coDept = $("coDept");
    const coCity = $("coCity");
    const coNotes = $("coNotes");

    const getPayMethod = () => {
      if (checkoutForm) {
        const v = new FormData(checkoutForm).get("pay_method");
        return (v || "card").toString().trim().toLowerCase();
      }
      const v = document.querySelector('input[name="pay_method"]:checked')?.value;
      return (v || "card").toString().trim().toLowerCase();
    };

    const updateGoCheckoutVisibility = () => {
      const btn = $("goCheckoutBtn");
      if (!btn) return;
      btn.style.display = cart.length ? "inline-flex" : "none";
    };

    // ========= Checkout Summary =========
    const renderCheckoutSummary = () => {
      const itemsWrap = $("sumItems");
      const elSubtotal = $("sumSubtotal");
      const elShipping = $("sumShipping");
      const elTotal = $("sumTotal");

      if (!itemsWrap || !elSubtotal || !elShipping || !elTotal) return;

      itemsWrap.innerHTML = "";

      cart.forEach((it) => {
        const price = getItemUnitPrice(it);
        const qty = Math.max(1, parseInt(it.qty || 1, 10));
        const line = price * qty;

        const div = document.createElement("div");
        div.className = "sum-item";
        div.innerHTML = `
          <div class="sum-thumb" style="background-image:url('${it.img || ""}')"></div>
          <div class="sum-info">
            <p class="sum-title">${it.title || "Producto BASALTO"}</p>
            <div class="sum-meta">
              ${(it.sleeve || "").trim()} · ${(it.color || "").trim()} · ${it.size ? `Talla ${(it.size || "").toUpperCase()} · ` : ""}x${qty}
              ${it.sku ? ` · <span style="color:var(--muted)">SKU ${it.sku}</span>` : ``}
            </div>
          </div>
          <div class="sum-price">
            <strong>${money(line)}</strong><br>
            <span style="color:var(--muted)">${money(price)} c/u</span>
          </div>
        `;
        itemsWrap.appendChild(div);
      });

      const subtotal = calcSubtotal(cart);
      const shipping = cart.length ? SHIPPING_FLAT : 0;
      const total = subtotal + shipping;

      elSubtotal.textContent = money(subtotal);
      elShipping.textContent = money(shipping);
      elTotal.textContent = money(total);
    };

    // ========= Drawer (mini carrito) =========
    const renderDrawer = () => {
      const itemsWrap = $("drawerItems");
      const empty = $("drawerEmpty");
      const elSub = $("drawerSubtotal");
      const elShip = $("drawerShipping");
      const elTot = $("drawerTotal");
      const badge = $("cartBadge");

      if (!itemsWrap || !empty || !elSub || !elShip || !elTot) return;

      itemsWrap.innerHTML = "";
      empty.style.display = cart.length ? "none" : "block";

      if (badge) {
        const count = cart.reduce((acc, it) => acc + Number(it.qty || 1), 0);
        badge.textContent = String(count);
        badge.style.display = count ? "inline-flex" : "none";
        badge.setAttribute("aria-label", `${count} items`);
      }

      cart.forEach((it, i) => {
        const price = getItemUnitPrice(it);
        const qty = Math.max(1, parseInt(it.qty || 1, 10));
        const line = price * qty;

        const div = document.createElement("div");
        div.className = "ditem";
        div.innerHTML = `
          <div class="dthumb" style="background-image:url('${it.img || ""}')"></div>
          <div class="dmeta">
            <p class="dtitle">${it.title || "Producto BASALTO"}</p>
            <div class="dsub">
              ${(it.sleeve || "").trim()} · ${(it.color || "").trim()} ${it.size ? `· Talla ${(it.size || "").toUpperCase()}` : ""}
              ${it.sku ? ` · SKU ${it.sku}` : ``}
            </div>

            <div class="drow2">
              <div class="dqty" aria-label="Cantidad">
                <button class="dqbtn" type="button" data-dqminus="${i}">−</button>
                <div class="dqval">${qty}</div>
                <button class="dqbtn" type="button" data-dqplus="${i}">+</button>
              </div>

              <div style="text-align:right;">
                <div class="dprice">${money(line)}</div>
                <div class="dsub">${money(price)} c/u</div>
              </div>
            </div>

            <div class="drow2">
              <button class="dremove" type="button" data-dremove="${i}">Eliminar</button>
            </div>
          </div>
        `;
        itemsWrap.appendChild(div);
      });

      const subtotal = calcSubtotal(cart);
      const shipping = cart.length ? SHIPPING_FLAT : 0;
      const total = subtotal + shipping;

      elSub.textContent = money(subtotal);
      elShip.textContent = money(shipping);
      elTot.textContent = money(total);

      updateGoCheckoutVisibility();
    };

    const openDrawer = () => {
      const d = $("cartDrawer");
      if (!d) return;
      d.classList.add("is-open");
      d.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      renderDrawer();
    };

    const closeDrawer = () => {
      const d = $("cartDrawer");
      if (!d) return;
      d.classList.remove("is-open");
      d.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    };

    // ========= Elements (Product Modal) =========
    const productModal = $("productModal");
    if (!productModal) return;

    const pmImg = $("pmImg");
    const pmTitle = $("pmTitle");
    const pmKicker = $("pmKicker");
    const pmPrice = $("pmPrice");
    const pmCompare = $("pmCompare");
    const pmColor = $("pmColor");
    const pmFabric = $("pmFabric");

    const pmNeckWrap = $("pmNeckWrap"); // puede no existir
    const pmNeck = $("pmNeck"); // puede no existir
    const pmSizeWrap = $("pmSizeWrap"); // puede no existir
    const pmSizeHint = $("pmSizeHint"); // puede no existir

    const pmQty = $("pmQty");
    const pmSize = $("pmSize");
    const qtyMinus = $("qtyMinus");
    const qtyPlus = $("qtyPlus");

    const addToCartBtn = resetBtn("addToCartBtn");
    const goCheckoutBtn = resetBtn("goCheckoutBtn");
    const buyNowBtn = resetBtn("buyNowBtn");

    // fallback DOM: encontrar span del cuello si no hay #pmNeck
    const getFallbackNeckSpan = () => {
      // busca el primer bloque "Cuello" dentro del modal
      const keys = Array.from(productModal.querySelectorAll(".mkey"));
      const cuelloKey = keys.find((k) => (k.textContent || "").trim().toLowerCase() === "cuello");
      if (!cuelloKey) return null;
      const wrap = cuelloKey.closest("div");
      if (!wrap) return null;
      return wrap.querySelector(".mval");
    };

    // ========= Build item from current =========
    const buildItemFromCurrent = (qty, size) => {
      const skuMap = currentProduct?.sku_map || {};
      const kind = (currentProduct?.kind || "shirt").toLowerCase();

      const availableSizes = getAvailableSizes(skuMap);
      let SIZE = normalizeSizeKey(size || "M");

      if (kind !== "shirt") {
        const one = availableSizes.find(isOneSize);
        SIZE = one ? normalizeSizeKey(one) : normalizeSizeKey(availableSizes[0] || "UNI");
      } else {
        if (!String(skuMap[SIZE] || "").trim() && availableSizes.length) {
          SIZE = normalizeSizeKey(availableSizes[0]);
        }
      }

      const chosenSku = String(skuMap[SIZE] || "").trim();

      return {
        sku: chosenSku,
        img: currentProduct?.img || "",
        title: currentProduct?.title || "Producto BASALTO",
        sleeve: currentProduct?.sleeve || "",
        color: currentProduct?.color || "",
        fabric: currentProduct?.fabric || "",
        price: normalizePrice(currentProduct?.price || 0).toFixed(2),
        compare: String(currentProduct?.compare || "0"),
        qty: Math.max(1, parseInt(qty || 1, 10)),
        size: SIZE,
        kind,
      };
    };

    // ========= Product Modal open/close =========
    const openProductModal = (data) => {
      currentProduct = data;

      const skuMap = data.sku_map || {};
      const kind = inferKind(data.kind, skuMap);

      if (pmImg) {
        pmImg.src = data.img || "";
        pmImg.alt = `${data.title || "Producto"} ${data.color || ""}`.trim();
      }

      if (pmTitle) pmTitle.textContent = data.title || "Producto BASALTO";
      if (pmPrice) pmPrice.textContent = normalizePrice(data.price).toFixed(2);
      if (pmCompare) pmCompare.textContent = data.compare ?? "0";
      if (pmColor) pmColor.textContent = data.color || "";
      if (pmFabric) pmFabric.textContent = data.fabric || "";

      if (pmKicker) {
        if (kind === "shirt") pmKicker.textContent = (data.sleeve || "Manga").toUpperCase();
        else pmKicker.textContent = "ACCESORIO";
      }

      // cuello (solo shirts)
      const showNeck = kind === "shirt";
      if (pmNeckWrap) pmNeckWrap.style.display = showNeck ? "" : "none";
      if (pmNeck) pmNeck.textContent = showNeck ? "-" : "";
      else {
        const neckSpan = getFallbackNeckSpan();
        if (neckSpan) neckSpan.textContent = showNeck ? "-" : "";
      }

      // tallas
      let sizes = getAvailableSizes(skuMap);

      // fallback fuerte: que NUNCA quede vacío en camisas
      if ((kind === "shirt") && (!sizes || !sizes.length)) {
        sizes = ["S", "M", "L", "XL", "XXL"];
      }

      if (pmSizeWrap) pmSizeWrap.style.display = (kind === "shirt") ? "" : "none";

      if (pmSize) {
        pmSize.innerHTML = "";

        if (kind === "shirt") {
          sizes.forEach((sz) => {
            const opt = document.createElement("option");
            opt.value = normalizeSizeKey(sz);
            opt.textContent = normalizeSizeKey(sz);
            pmSize.appendChild(opt);
          });

          // si por cualquier razón no se agregó nada, mete fallback
          if (pmSize.options.length === 0) {
            ["S", "M", "L", "XL", "XXL"].forEach((sz) => {
              const opt = document.createElement("option");
              opt.value = sz;
              opt.textContent = sz;
              pmSize.appendChild(opt);
            });
          }

          pmSize.value = pmSize.options.length ? pmSize.options[0].value : "M";
          if (pmSizeHint) pmSizeHint.style.display = "";
          pmSize.disabled = false;
        } else {
          if (pmSizeHint) pmSizeHint.style.display = "none";
          pmSize.disabled = true;
        }
      }

      if (pmQty) pmQty.value = 1;

      openModalById("productModal");
      updateGoCheckoutVisibility();
    };

    const closeProductModal = () => {
      closeModalById("productModal");
      currentProduct = null;
    };

    const openCheckout = () => {
      openModalById("checkoutModal");

      const checked = document.querySelector('input[name="pay_method"]:checked');
      if (!checked) {
        const cardRadio = document.querySelector('input[name="pay_method"][value="card"]');
        if (cardRadio) cardRadio.checked = true;
      }

      const method = getPayMethod();
      if (transferBox) transferBox.style.display = method === "transfer" ? "block" : "none";
      if (transferRefHint) transferRefHint.textContent = "Se genera al confirmar";

      renderCheckoutSummary();
    };

    const closeCheckout = () => closeModalById("checkoutModal");

    // ========= Events =========

    // Abrir modal al click "Ver"
    document.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".js-open-modal");
      if (!btn) return;

      ev.preventDefault();

      const skuMap = parseSkuMap(btn.dataset.skuMap || "{}");

      const hasAnySku = skuMap && Object.values(skuMap).some((v) => String(v || "").trim());
      const cardEl = btn.closest(".card");
      if (cardEl) cardEl.classList.toggle("is-soldout", !hasAnySku);

      if (!hasAnySku) {
        alert("Sold out — pronto re-stock.");
        return;
      }

      openProductModal({
        img: btn.dataset.img || "",
        title: btn.dataset.title || "Producto BASALTO",
        sleeve: btn.dataset.sleeve || "",
        color: btn.dataset.color || "",
        price: normalizePrice(btn.dataset.price || "0"),
        compare: btn.dataset.compare || "0",
        fabric: btn.dataset.fabric || "",
        kind: btn.dataset.kind || "",
        sku_map: skuMap,
      });
    });

    // Cerrar product modal (backdrop / X)
    productModal.addEventListener("click", (e) => {
      if (e.target.matches("[data-close-modal]")) closeProductModal();
    });

    // Cerrar checkout modal
    document.addEventListener("click", (e) => {
      if (e.target.matches("[data-close-checkout]")) closeCheckout();
    });

    // Cerrar drawer
    document.addEventListener("click", (e) => {
      if (e.target.matches("[data-close-drawer]")) closeDrawer();
    });

    // Escape
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (productModal.classList.contains("is-open")) closeProductModal();
      if (checkoutModal && checkoutModal.classList.contains("is-open")) closeCheckout();
      const d = $("cartDrawer");
      if (d && d.classList.contains("is-open")) closeDrawer();
    });

    // Qty +/- modal producto
    if (qtyMinus && pmQty) {
      qtyMinus.addEventListener("click", () => {
        pmQty.value = Math.max(1, parseInt(pmQty.value || "1", 10) - 1);
      });
    }
    if (qtyPlus && pmQty) {
      qtyPlus.addEventListener("click", () => {
        pmQty.value = Math.max(1, parseInt(pmQty.value || "1", 10) + 1);
      });
    }

    // Agregar al pedido (merge)
    if (addToCartBtn) {
      addToCartBtn.addEventListener("click", () => {
        if (!currentProduct) return;

        const qty = Math.max(1, parseInt(pmQty?.value || "1", 10));
        const size = normalizeSizeKey(pmSize?.value || "M");

        const item = buildItemFromCurrent(qty, size);
        if (!item.sku) {
          alert("Esta talla no está disponible en este momento.");
          return;
        }

        addOrMerge(item);
        renderDrawer();
        updateGoCheckoutVisibility();

        addToCartBtn.textContent = "Agregado ✓";
        setTimeout(() => (addToCartBtn.textContent = "Agregar al pedido"), 900);
      });
    }

    // Ir a checkout
    if (goCheckoutBtn) {
      goCheckoutBtn.addEventListener("click", () => {
        if (cart.length === 0 && currentProduct) {
          const qty = Math.max(1, parseInt(pmQty?.value || "1", 10));
          const size = normalizeSizeKey(pmSize?.value || "M");
          addOrMerge(buildItemFromCurrent(qty, size));
        }
        closeProductModal();
        openCheckout();
      });
    }

    // Comprar ahora
    if (buyNowBtn) {
      buyNowBtn.addEventListener("click", () => {
        if (!currentProduct) return;

        const qty = Math.max(1, parseInt(pmQty?.value || "1", 10));
        const size = normalizeSizeKey(pmSize?.value || "M");

        const item = buildItemFromCurrent(qty, size);
        if (!item.sku) {
          alert("Esta talla no está disponible en este momento.");
          return;
        }

        addOrMerge(item);
        closeProductModal();
        openCheckout();
      });
    }

    // Toggle método de pago
    document.querySelectorAll('input[name="pay_method"]').forEach((r) => {
      r.addEventListener("change", () => {
        const method = getPayMethod();
        if (transferBox) transferBox.style.display = method === "transfer" ? "block" : "none";
        if (transferRefHint) transferRefHint.textContent = "Se genera al confirmar";
      });
    });

    // Drawer qty +/- / remove
    document.addEventListener("click", (e) => {
      const minus = e.target.closest("[data-dqminus]");
      const plus = e.target.closest("[data-dqplus]");
      const rem = e.target.closest("[data-dremove]");

      if (minus) {
        const i = parseInt(minus.getAttribute("data-dqminus"), 10);
        if (cart[i]) {
          cart[i].qty = Math.max(1, Number(cart[i].qty || 1) - 1);
          renderDrawer();
        }
      }

      if (plus) {
        const i = parseInt(plus.getAttribute("data-dqplus"), 10);
        if (cart[i]) {
          cart[i].qty = Math.max(1, Number(cart[i].qty || 1) + 1);
          renderDrawer();
        }
      }

      if (rem) {
        const i = parseInt(rem.getAttribute("data-dremove"), 10);
        if (cart[i]) {
          cart.splice(i, 1);
          renderDrawer();
        }
      }
    });

    // Drawer -> checkout
    const drawerCheckout = $("drawerCheckout");
    if (drawerCheckout) {
      drawerCheckout.addEventListener("click", () => {
        if (cart.length === 0) return alert("Tu carrito está vacío.");
        closeDrawer();
        openCheckout();
      });
    }

    // Header cart button -> drawer
    const cartBtn = $("cartBtn");
    if (cartBtn) {
      cartBtn.addEventListener("click", (e) => {
        e.preventDefault();
        openDrawer();
      });
    }

    /* ==========================================
       Checkout submit -> API -> Wompi / WhatsApp
       - Card: abre Wompi directo
       - Transfer: abre WhatsApp
       - Siempre crea la orden
    ========================================== */
    if (checkoutForm) {
      checkoutForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (cart.length === 0) {
          alert("Tu pedido está vacío. Seleccioná al menos un producto.");
          return;
        }

        const full_name = (coName?.value || "").trim();
        const phone = (coPhone?.value || "").trim();
        const address_line1 = (coAddress1?.value || "").trim();

        if (!full_name || !phone || !address_line1) {
          alert("Completa nombre, teléfono y dirección.");
          return;
        }

        const chosenMethod = getPayMethod();

        let pendingWin = null;
        if (chosenMethod === "card") {
          pendingWin = window.open("", "_blank");
        }

        const payload = {
          country: "El Salvador",
          full_name,
          phone,
          address_line1,
          address_line2: (coAddress2?.value || "").trim(),
          department: (coDept?.value || "").trim(),
          city: (coCity?.value || "").trim(),
          notes: (coNotes?.value || "").trim(),
          payment_method: chosenMethod,
          items: cart.map((it) => ({
            sku: it.sku || "",
            title: it.title,
            sleeve: it.sleeve,
            color: it.color,
            size: (it.size || "").toUpperCase(),
            fabric: it.fabric || "",
            img: it.img || "",
            qty: it.qty || 1,
            unit_price: String(it.price ?? it.unit_price ?? "0").replace(/[^0-9.]/g, ""),
          })),
        };

        if (confirmOrderBtn) {
          confirmOrderBtn.disabled = true;
          confirmOrderBtn.textContent = "Generando orden…";
        }

        try {
          const res = await fetch("/api/orders/create/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

          const raw = await res.text();
          if (!res.ok) {
            console.log("CREATE_ORDER ERROR:", raw);
            throw new Error(raw || "Error creando orden");
          }

          const data = JSON.parse(raw);

          if (data && data.ok === false) {
            throw new Error(data.detail || "No se pudo crear la orden");
          }

          const orderNumber = data.order_number || "";

          if (transferRefHint) transferRefHint.textContent = orderNumber || "Tu número de orden";

          if (chosenMethod === "card") {
            if (data.payment_link) {
              if (pendingWin && pendingWin.location) pendingWin.location.href = data.payment_link;
              else window.location.href = data.payment_link;

              cart.length = 0;
              renderDrawer();
              closeCheckout();
              return;
            }
            try { if (pendingWin && !pendingWin.closed) pendingWin.close(); } catch (_) {}
            alert("Orden creada, pero no se pudo generar el link de Wompi. Intentá de nuevo.");
            return;
          }

          if (chosenMethod === "transfer") {
            if (data.whatsapp_url) {
              const w = window.open(data.whatsapp_url, "_blank", "noopener");
              if (!w) window.location.href = data.whatsapp_url;

              cart.length = 0;
              renderDrawer();
              closeCheckout();
              return;
            }

            alert("Orden creada. No se pudo abrir WhatsApp automáticamente.");
            return;
          }

          alert("Orden creada.");
          cart.length = 0;
          renderDrawer();
          closeCheckout();
        } catch (err) {
          try { if (pendingWin && !pendingWin.closed) pendingWin.close(); } catch (_) {}
          alert("No se pudo crear la orden: " + (err?.message || err));
        } finally {
          if (confirmOrderBtn) {
            confirmOrderBtn.disabled = false;
            confirmOrderBtn.textContent = "Confirmar y enviar";
          }
        }
      });
    }

    // Inicial
    updateGoCheckoutVisibility();
    renderDrawer();

    // Debug
    window.BASALTO_CART = cart;
  });
})();

/* ===========================
   Catalog filters (tab-aware + counter)
=========================== */
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const state = { sleeve: "all", color: "all", q: "" };

    const search = document.getElementById("filterSearch");
    const clear = document.getElementById("filterClear");
    const resultsText = document.getElementById("resultsText");

    const tabMen = document.getElementById("tab-men");
    const tabKids = document.getElementById("tab-kids");
    const tabWomen = document.getElementById("tab-women");

    function norm(s) {
      return String(s || "").trim().toLowerCase();
    }

    function getActiveGrid() {
      if (tabKids && tabKids.checked) return document.getElementById("catalogGrid-kids");
      if (tabWomen && tabWomen.checked) return document.getElementById("catalogGrid-women");
      return document.getElementById("catalogGrid-men");
    }

    function setResults(shown, total) {
      if (!resultsText) return;
      if (total === 0) {
        resultsText.textContent = "Sin resultados";
        return;
      }
      resultsText.textContent = `Mostrando ${shown} de ${total}`;
    }

    function apply() {
      const grid = getActiveGrid();
      if (!grid) {
        setResults(0, 0);
        return;
      }

      const cards = Array.from(grid.querySelectorAll(".card"));
      const total = cards.length;

      let shown = 0;

      cards.forEach((card) => {
        const sleeve = norm(card.getAttribute("data-sleeve"));
        const color = norm(card.getAttribute("data-color"));
        const text = norm(card.innerText);

        const okSleeve = state.sleeve === "all" || sleeve === norm(state.sleeve);
        const okColor = state.color === "all" || color === norm(state.color);
        const okQ = !state.q || text.includes(norm(state.q));

        const ok = okSleeve && okColor && okQ;
        card.style.display = ok ? "" : "none";
        if (ok) shown++;
      });

      setResults(shown, total);
    }

    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".fbtn");
      if (!btn) return;

      const filter = btn.getAttribute("data-filter");
      const value = btn.getAttribute("data-value");
      if (!filter || !value) return;

      state[filter] = value;

      const group = btn.closest(".filter-group");
      if (group) {
        group.querySelectorAll(".fbtn").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
      }

      apply();
    });

    if (search) {
      search.addEventListener("input", () => {
        state.q = search.value || "";
        apply();
      });
    }

    if (clear) {
      clear.addEventListener("click", () => {
        state.sleeve = "all";
        state.color = "all";
        state.q = "";

        if (search) search.value = "";

        document.querySelectorAll('.fbtn[data-filter="sleeve"]').forEach((b) => b.classList.remove("is-active"));
        document.querySelector('.fbtn[data-filter="sleeve"][data-value="all"]')?.classList.add("is-active");

        document.querySelectorAll('.fbtn[data-filter="color"]').forEach((b) => b.classList.remove("is-active"));
        document.querySelector('.fbtn[data-filter="color"][data-value="all"]')?.classList.add("is-active");

        apply();
      });
    }

    function bindTab(radio) {
      if (!radio) return;
      radio.addEventListener("change", () => apply());
    }
    bindTab(tabMen);
    bindTab(tabKids);
    bindTab(tabWomen);

    apply();
  });
})();
