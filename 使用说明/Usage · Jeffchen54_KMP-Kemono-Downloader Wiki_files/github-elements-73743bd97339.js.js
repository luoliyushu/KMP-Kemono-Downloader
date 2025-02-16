"use strict";(globalThis.webpackChunk=globalThis.webpackChunk||[]).push([["github-elements"],{10361:(e,t,n)=>{var i=n(98184),r=n(38257),s=n(14840),a=n(57260),o=n(13002),l=n(73921),u=n(27034),d=n(51941),c=n(88309),h=n(40987),m=n(57852),p=n(88823);window.IncludeFragmentElement.prototype.fetch=e=>(e.headers.append("X-Requested-With","XMLHttpRequest"),window.fetch(e));var f=n(97895),g=n(76006),v=function(e,t,n,i){var r,s=arguments.length,a=s<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,n):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,n,i);else for(var o=e.length-1;o>=0;o--)(r=e[o])&&(a=(s<3?r(a):s>3?r(t,n,a):r(t,n))||a);return s>3&&a&&Object.defineProperty(t,n,a),a};let w=class GitCloneHelpElement extends HTMLElement{updateURL(e){let t=e.currentTarget,n=t.getAttribute("data-url")||"";if(this.helpField.value=n,t.matches(".js-git-protocol-clone-url"))for(let e of this.helpTexts)e.textContent=n;for(let e of this.cloneURLButtons)e.classList.remove("selected");t.classList.add("selected")}};function b(e,t){if(t.has(e))throw TypeError("Cannot initialize the same private elements twice on an object")}function y(e,t){return t.get?t.get.call(e):t.value}function E(e,t,n){if(t.set)t.set.call(e,n);else{if(!t.writable)throw TypeError("attempted to set read only private field");t.value=n}}function x(e,t,n){if(!t.has(e))throw TypeError("attempted to "+n+" private field on non-instance");return t.get(e)}function C(e,t){var n=x(e,t,"get");return y(e,n)}function L(e,t,n){b(e,t),t.set(e,n)}function T(e,t,n){var i=x(e,t,"set");return E(e,i,n),n}function k(e,t){let n=[],i=0;for(let r=0;r<e.length;r++){let s=e[r],a=t.indexOf(s,i);if(-1===a)break;i=a+1,n.push(a)}return n}v([g.fA],w.prototype,"helpField",void 0),v([g.GO],w.prototype,"helpTexts",void 0),v([g.GO],w.prototype,"cloneURLButtons",void 0),w=v([g.Ih],w);var _=new WeakMap,S=new WeakMap,M=new WeakMap,A=new WeakMap;let q=class MarkedTextElement extends HTMLElement{get query(){return this.ownerInput?this.ownerInput.value:this.getAttribute("query")||""}set query(e){this.setAttribute("query",e)}get ownerInput(){let e=this.ownerDocument.getElementById(this.getAttribute("data-owner-input")||"");return e instanceof HTMLInputElement?e:null}connectedCallback(){this.handleEvent(),this.ownerInput?.addEventListener("input",this),T(this,M,new MutationObserver(()=>this.handleEvent()))}handleEvent(){C(this,A)&&cancelAnimationFrame(C(this,A)),T(this,A,requestAnimationFrame(()=>this.mark()))}disconnectedCallback(){this.ownerInput?.removeEventListener("input",this),C(this,M).disconnect()}mark(){let e=this.textContent||"",t=this.query;if(e===C(this,_)&&t===C(this,S))return;T(this,_,e),T(this,S,t),C(this,M).disconnect();let n=0,i=document.createDocumentFragment();for(let r of(this.positions||k)(t,e)){if(Number(r)!==r||r<n||r>e.length)continue;let t=e.slice(n,r);""!==t&&i.appendChild(document.createTextNode(e.slice(n,r))),n=r+1;let s=document.createElement("mark");s.textContent=e[r],i.appendChild(s)}i.appendChild(document.createTextNode(e.slice(n))),this.replaceChildren(i),C(this,M).observe(this,{attributes:!0,childList:!0,subtree:!0})}constructor(...e){super(...e),L(this,_,{writable:!0,value:""}),L(this,S,{writable:!0,value:""}),L(this,M,{writable:!0,value:void 0}),L(this,A,{writable:!0,value:void 0})}};q.observedAttributes=["query","data-owner-input"],window.customElements.get("marked-text")||(window.MarkedTextElement=q,window.customElements.define("marked-text",q));var I=n(81775);let R=class PasswordStrengthElement extends HTMLElement{connectedCallback(){this.addEventListener("input",P)}disconnectedCallback(){this.removeEventListener("input",P)}};function P(e){let t=e.currentTarget;if(!(t instanceof R))return;let n=e.target;if(!(n instanceof HTMLInputElement))return;let i=n.form;if(!(i instanceof HTMLFormElement))return;let r=N(n.value,{minimumCharacterCount:Number(t.getAttribute("minimum-character-count")),passphraseLength:Number(t.getAttribute("passphrase-length"))});if(r.valid){n.setCustomValidity("");let e=t.querySelector("dl.form-group");e&&(e.classList.remove("errored"),e.classList.add("successed"))}else n.setCustomValidity(t.getAttribute("invalid-message")||"Invalid");O(t,r),(0,I.G)(i)}function N(e,t){let n={valid:!1,hasMinimumCharacterCount:e.length>=t.minimumCharacterCount,hasMinimumPassphraseLength:0!==t.passphraseLength&&e.length>=t.passphraseLength,hasLowerCase:/[a-z]/.test(e),hasNumber:/\d/.test(e)};return n.valid=n.hasMinimumPassphraseLength||n.hasMinimumCharacterCount&&n.hasLowerCase&&n.hasNumber,n}function O(e,t){let n=e.querySelector("[data-more-than-n-chars]"),i=e.querySelector("[data-min-chars]"),r=e.querySelector("[data-number-requirement]"),s=e.querySelector("[data-letter-requirement]"),a=e.getAttribute("error-class")?.split(" ").filter(e=>e.length>0)||[],o=e.getAttribute("pass-class")?.split(" ").filter(e=>e.length>0)||[];for(let e of[n,i,r,s])e?.classList.remove(...a,...o);if(t.hasMinimumPassphraseLength&&n)n.classList.add(...o);else if(t.valid)i.classList.add(...o),r.classList.add(...o),s.classList.add(...o);else{let e=t.hasMinimumCharacterCount?o:a,l=t.hasNumber?o:a,u=t.hasLowerCase?o:a;n?.classList.add(...a),i.classList.add(...e),r.classList.add(...l),s.classList.add(...u)}}window.customElements.get("password-strength")||(window.PasswordStrengthElement=R,window.customElements.define("password-strength",R));var z=n(87551),j=function(e,t,n,i){var r,s=arguments.length,a=s<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,n):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,n,i);else for(var o=e.length-1;o>=0;o--)(r=e[o])&&(a=(s<3?r(a):s>3?r(t,n,a):r(t,n))||a);return s>3&&a&&Object.defineProperty(t,n,a),a};let B=class PollIncludeFragmentElement extends u.Z{async fetch(e,t=1e3){let n=await super.fetch(e);return 202===n.status?(await new Promise(e=>setTimeout(e,t)),this.fetch(e,1.5*t)):n}connectedCallback(){super.connectedCallback(),this.retryButton&&this.retryButton.addEventListener("click",()=>{this.refetch()})}};j([g.fA],B.prototype,"retryButton",void 0),B=j([g.Ih],B);var H=n(10160);function F(e,t,n){let i=e.lastIndexOf(t,n-1);if(-1===i)return;let r=e.lastIndexOf(" ",n-1);if(r>i)return;let s=e.lastIndexOf("\n",n-1);if(s>i)return;let a=e[i-1];if(a&&"\n"!==a)return;let o=e.substring(i+t.length,n);return{word:o,position:i+t.length,beginningOfLine:W(a)}}let W=e=>void 0===e||/\n/.test(e),D=["position:absolute;","overflow:auto;","word-wrap:break-word;","top:0px;","left:-9999px;"],V=["box-sizing","font-family","font-size","font-style","font-variant","font-weight","height","letter-spacing","line-height","max-height","min-height","padding-bottom","padding-left","padding-right","padding-top","border-bottom","border-left","border-right","border-top","text-decoration","text-indent","text-transform","width","word-spacing"],$=new WeakMap;function U(e,t){let n,i;let r=e.nodeName.toLowerCase();if("textarea"!==r&&"input"!==r)throw Error("expected textField to a textarea or input");let s=$.get(e);if(s&&s.parentElement===e.parentElement)s.textContent="";else{s=document.createElement("div"),$.set(e,s);let t=window.getComputedStyle(e),n=D.slice(0);"textarea"===r?n.push("white-space:pre-wrap;"):n.push("white-space:nowrap;");for(let e=0,i=V.length;e<i;e++){let i=V[e];n.push(`${i}:${t.getPropertyValue(i)};`)}s.style.cssText=n.join(" ")}let a=document.createElement("span");if(a.style.cssText="position: absolute;",a.textContent="\xa0","number"==typeof t){let r=e.value.substring(0,t);r&&(n=document.createTextNode(r)),(r=e.value.substring(t))&&(i=document.createTextNode(r))}else{let t=e.value;t&&(n=document.createTextNode(t))}if(n&&s.appendChild(n),s.appendChild(a),i&&s.appendChild(i),!s.parentElement){if(!e.parentElement)throw Error("textField must have a parentElement to mirror");e.parentElement.insertBefore(s,e)}return s.scrollTop=e.scrollTop,s.scrollLeft=e.scrollLeft,{mirror:s,marker:a}}function G(e,t=e.selectionEnd){let{mirror:n,marker:i}=U(e,t),r=n.getBoundingClientRect(),s=i.getBoundingClientRect();return setTimeout(()=>{n.remove()},5e3),{top:s.top-r.top,left:s.left-r.left}}let Z=new WeakMap,Y=class SlashCommandExpander{destroy(){this.input.removeEventListener("paste",this.onpaste),this.input.removeEventListener("input",this.oninput),this.input.removeEventListener("keydown",this.onkeydown),this.input.removeEventListener("blur",this.onblur)}activate(e,t){this.input===document.activeElement&&this.setMenu(e,t)}deactivate(){let e=this.menu,t=this.combobox;return!!e&&!!t&&(this.menu=null,this.combobox=null,e.removeEventListener("combobox-commit",this.oncommit),e.removeEventListener("mousedown",this.onmousedown),t.destroy(),e.remove(),!0)}setMenu(e,t){this.deactivate(),this.menu=t,t.id||(t.id=`text-expander-${Math.floor(1e5*Math.random()).toString()}`),this.expander.append(t);let n=t.querySelector(".js-command-list-container");n?this.combobox=new H.Z(this.input,n):this.combobox=new H.Z(this.input,t);let{top:i,left:r}=G(this.input,e.position),s=parseInt(window.getComputedStyle(this.input).fontSize);t.style.top=`${i+s}px`,t.style.left=`${r}px`,this.combobox.start(),t.addEventListener("combobox-commit",this.oncommit),t.addEventListener("mousedown",this.onmousedown),this.combobox.navigate(1)}setValue(e){if(null==e)return;let t=this.match;if(!t)return;let{cursor:n,value:i}=this.replaceCursorMark(e);i=i?.length===0?i:`${i} `;let r=t.position-t.key.length,s=t.position+t.text.length;this.input.focus();let a=!1;try{this.input.setSelectionRange(r,s),a=document.execCommand("insertText",!1,i)}catch(e){a=!1}if(!a){let e=this.input.value.substring(0,t.position-t.key.length),n=this.input.value.substring(t.position+t.text.length);this.input.value=e+i+n}this.deactivate(),n=r+(n||i.length),this.input.selectionStart=n,this.input.selectionEnd=n}replaceCursorMark(e){let t=/%cursor%/gm,n=t.exec(e);return n?{cursor:n.index,value:e.replace(t,"")}:{cursor:null,value:e}}async onCommit({target:e}){if(!(e instanceof HTMLElement)||!this.combobox)return;let t=this.match;if(!t)return;let i={item:e,key:t.key,value:null},r=new CustomEvent("text-expander-value",{cancelable:!0,detail:i}),s=!this.expander.dispatchEvent(r),{onValue:a}=await n.e("app_assets_modules_github_slash-command-expander-element_slash-command-suggester_ts").then(n.bind(n,72564));await a(this.expander,t.key,e),!s&&i.value&&this.setValue(i.value)}onBlur(){if(this.interactingWithMenu){this.interactingWithMenu=!1;return}this.deactivate()}onPaste(){this.justPasted=!0}async delay(e){return new Promise(t=>setTimeout(t,e))}async onInput(){if(this.justPasted){this.justPasted=!1;return}let e=this.findMatch();if(e){if(this.match=e,await this.delay(this.appropriateDelay()),this.match!==e)return;let t=await this.notifyProviders(e);if(!this.match)return;t?this.activate(e,t):this.deactivate()}else this.match=null,this.deactivate()}appropriateDelay(){return 250}findMatch(){let e=this.input.selectionEnd,t=this.input.value;for(let n of this.expander.keys){let i=F(t,n,e);if(i)return{text:i.word,key:n,position:i.position,beginningOfLine:i.beginningOfLine}}}async notifyProviders(e){let t=[],i=e=>t.push(e),r=new CustomEvent("text-expander-change",{cancelable:!0,detail:{provide:i,text:e.text,key:e.key}}),s=!this.expander.dispatchEvent(r);if(s)return;let{onChange:a}=await n.e("app_assets_modules_github_slash-command-expander-element_slash-command-suggester_ts").then(n.bind(n,72564));a(this.expander,e.key,i,e.text);let o=await Promise.all(t),l=o.filter(e=>e.matched).map(e=>e.fragment);return l[0]}onMousedown(){this.interactingWithMenu=!0}onKeydown(e){"Escape"===e.key&&this.deactivate()&&(e.stopImmediatePropagation(),e.preventDefault())}constructor(e,t){this.expander=e,this.input=t,this.combobox=null,this.menu=null,this.match=null,this.justPasted=!1,this.oninput=this.onInput.bind(this),this.onpaste=this.onPaste.bind(this),this.onkeydown=this.onKeydown.bind(this),this.oncommit=this.onCommit.bind(this),this.onmousedown=this.onMousedown.bind(this),this.onblur=this.onBlur.bind(this),this.interactingWithMenu=!1,t.addEventListener("paste",this.onpaste),t.addEventListener("input",this.oninput),t.addEventListener("keydown",this.onkeydown),t.addEventListener("blur",this.onblur)}},K=class SlashCommandExpanderElement extends HTMLElement{get keys(){let e=this.getAttribute("keys");return e?e.split(" "):[]}connectedCallback(){let e=this.querySelector('input[type="text"], textarea');if(!(e instanceof HTMLInputElement||e instanceof HTMLTextAreaElement))return;let t=new Y(this,e);Z.set(this,t)}disconnectedCallback(){let e=Z.get(this);e&&(e.destroy(),Z.delete(this))}setValue(e){let t=Z.get(this);t&&t.setValue(e)}setMenu(e,t=!1){let n=Z.get(this);n&&n.match&&(t&&(n.interactingWithMenu=!0),n.setMenu(n.match,e))}closeMenu(){let e=Z.get(this);e&&e.setValue("")}isLoading(){let e=this.getElementsByClassName("js-slash-command-expander-loading")[0];if(e){let t=e.cloneNode(!0);t.classList.remove("d-none"),this.setMenu(t)}}showError(){let e=this.getElementsByClassName("js-slash-command-expander-error")[0];if(e){let t=e.cloneNode(!0);t.classList.remove("d-none"),this.setMenu(t)}}};window.customElements.get("slash-command-expander")||(window.SlashCommandExpanderElement=K,window.customElements.define("slash-command-expander",K));var X=function(e,t,n,i){var r,s=arguments.length,a=s<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,n):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,n,i);else for(var o=e.length-1;o>=0;o--)(r=e[o])&&(a=(s<3?r(a):s>3?r(t,n,a):r(t,n))||a);return s>3&&a&&Object.defineProperty(t,n,a),a};let J=class TextSuggesterElement extends HTMLElement{acceptSuggestion(){this.suggestion?.textContent&&(this.input.value=this.suggestion.textContent,this.input.dispatchEvent(new Event("input")),this.suggestionContainer&&(this.suggestionContainer.hidden=!0),this.input.focus())}};function Q(e,t){if(t.has(e))throw TypeError("Cannot initialize the same private elements twice on an object")}function ee(e,t){return t.get?t.get.call(e):t.value}function et(e,t,n){if(t.set)t.set.call(e,n);else{if(!t.writable)throw TypeError("attempted to set read only private field");t.value=n}}function en(e,t,n){if(!t.has(e))throw TypeError("attempted to "+n+" private field on non-instance");return t.get(e)}function ei(e,t){var n=en(e,t,"get");return ee(e,n)}function er(e,t,n){Q(e,t),t.set(e,n)}function es(e,t,n){var i=en(e,t,"set");return et(e,i,n),n}function ea(e){return Boolean(e instanceof Set||e&&"object"==typeof e&&"size"in e&&"add"in e&&"delete"in e&&"clear"in e)}X([g.fA],J.prototype,"input",void 0),X([g.fA],J.prototype,"suggestionContainer",void 0),X([g.fA],J.prototype,"suggestion",void 0),J=X([g.Ih],J);var eo=new WeakMap,el=new WeakMap,eu=new WeakMap,ed=new WeakMap,ec=new WeakMap,eh=new WeakMap;let em=class VirtualFilterInputElement extends HTMLElement{static get observedAttributes(){return["src","loading","data-property","aria-owns"]}get filtered(){if(ei(this,eh))return ei(this,eh);if(this.hasAttribute("aria-owns")){let e=this.ownerDocument.getElementById(this.getAttribute("aria-owns")||"");e&&ea(e)&&es(this,eh,e)}return es(this,eh,ei(this,eh)||new Set)}set filtered(e){es(this,eh,e)}get input(){return this.querySelector("input, textarea")}get src(){return this.getAttribute("src")||""}set src(e){this.setAttribute("src",e)}get loading(){return"lazy"===this.getAttribute("loading")?"lazy":"eager"}set loading(e){this.setAttribute("loading",e)}get accept(){return this.getAttribute("accept")||""}set accept(e){this.setAttribute("accept",e)}get property(){return this.getAttribute("data-property")||""}set property(e){this.setAttribute("data-property",e)}reset(){this.filtered.clear(),es(this,ec,new Set)}clear(){this.input&&(this.input.value="",this.input.dispatchEvent(new Event("input")))}attributeChangedCallback(e,t,n){let i=this.isConnected&&this.src,r="eager"===this.loading,s=t!==n;("src"===e||"data-property"===e)&&s&&(es(this,eu,null),ei(this,ed)&&clearTimeout(ei(this,ed))),i&&r&&("src"===e||"loading"===e||"accept"===e||"data-property"===e)&&s?(cancelAnimationFrame(ei(this,el)),es(this,el,requestAnimationFrame(()=>this.load()))):"aria-owns"===e&&es(this,eh,null)}connectedCallback(){this.src&&"eager"===this.loading&&(cancelAnimationFrame(ei(this,el)),es(this,el,requestAnimationFrame(()=>this.load())));let e=this.input;if(!e)return;let t=this.getAttribute("aria-owns");null!==t&&this.attributeChangedCallback("aria-owns","",t),e.setAttribute("autocomplete","off"),e.setAttribute("spellcheck","false"),this.src&&"lazy"===this.loading&&(document.activeElement===e?this.load():e.addEventListener("focus",()=>{this.load()},{once:!0})),e.addEventListener("input",this)}disconnectedCallback(){this.input?.removeEventListener("input",this)}handleEvent(e){"input"===e.type&&(ei(this,ed)&&clearTimeout(ei(this,ed)),es(this,ed,window.setTimeout(()=>this.filterItems(),(this.input?.value?.length,300))))}async load(){ei(this,eo)?.abort(),es(this,eo,new AbortController);let{signal:e}=ei(this,eo);if(!this.src)throw Error("missing src");if(await new Promise(e=>setTimeout(e,0)),!e.aborted){this.dispatchEvent(new Event("loadstart"));try{let t=await this.fetch(this.request(),{signal:e,headers:{"X-Requested-With":"XMLHttpRequest"}});if(location.origin+this.src!==t.url)return;if(!t.ok)throw Error(`Failed to load resource: the server responded with a status of ${t.status}`);es(this,ec,new Set((await t.json())[this.property])),es(this,eu,null),this.dispatchEvent(new Event("loadend"))}catch(t){if(e.aborted){this.dispatchEvent(new Event("loadend"));return}throw(async()=>{this.dispatchEvent(new Event("error")),this.dispatchEvent(new Event("loadend"))})(),t}this.filtered.clear(),this.filterItems()}}request(){return new Request(this.src,{method:"GET",credentials:"same-origin",headers:{Accept:this.accept||"application/json"}})}fetch(e,t){return fetch(e,t)}filterItems(){let e;let t=this.input?.value.trim()??"",n=ei(this,eu);if(es(this,eu,t),t!==n){for(let i of(this.dispatchEvent(new CustomEvent("virtual-filter-input-filter")),n&&t.includes(n)?e=this.filtered:(e=ei(this,ec),this.filtered.clear()),e))this.filter(i,t)?this.filtered.add(i):this.filtered.delete(i);this.dispatchEvent(new CustomEvent("virtual-filter-input-filtered"))}}constructor(...e){super(...e),er(this,eo,{writable:!0,value:void 0}),er(this,el,{writable:!0,value:0}),er(this,eu,{writable:!0,value:null}),er(this,ed,{writable:!0,value:void 0}),er(this,ec,{writable:!0,value:new Set}),er(this,eh,{writable:!0,value:null}),this.filter=(e,t)=>String(e).includes(t)}};function ep(e,t){if(t.has(e))throw TypeError("Cannot initialize the same private elements twice on an object")}function ef(e,t){return t.get?t.get.call(e):t.value}function eg(e,t,n){if(t.set)t.set.call(e,n);else{if(!t.writable)throw TypeError("attempted to set read only private field");t.value=n}}function ev(e,t,n){if(!t.has(e))throw TypeError("attempted to "+n+" private field on non-instance");return t.get(e)}function ew(e,t){var n=ev(e,t,"get");return ef(e,n)}function eb(e,t,n){ep(e,t),t.set(e,n)}function ey(e,t,n){var i=ev(e,t,"set");return eg(e,i,n),n}window.customElements.get("virtual-filter-input")||(window.VirtualFilterInputElement=em,window.customElements.define("virtual-filter-input",em));let eE=new IntersectionObserver(e=>{for(let t of e)t.isIntersecting&&t.target instanceof eA&&"eager"===t.target.updating&&t.target.update()});var ex=new WeakMap,eC=new WeakMap,eL=new WeakMap,eT=new WeakMap,ek=new WeakMap,e_=new WeakMap,eS=new WeakMap;let eM=Symbol.iterator,eA=class VirtualListElement extends HTMLElement{static get observedAttributes(){return["data-updating","aria-activedescendant"]}get updating(){return"lazy"===this.getAttribute("data-updating")?"lazy":"eager"}set updating(e){this.setAttribute("data-updating",e)}get size(){return ew(this,eC).size}get range(){let e=this.getBoundingClientRect().height,{scrollTop:t}=this,n=`${t}-${e}`;if(ew(this,ek).has(n))return ew(this,ek).get(n);let i=0,r=0,s=0,a=0,o=ew(this,eL);for(let n of ew(this,eC)){let l=o.get(n)||ew(this,eT);if(s+l<t)s+=l,i+=1,r+=1;else if(a-l<e)a+=l,r+=1;else if(a>=e)break}return[i,r]}get list(){let e=this.querySelector("ul, ol, tbody");if(!e)throw Error("virtual-list must have a container element inside: any of <ul>, <ol>, <tbody>");return e}attributeChangedCallback(e,t,n){if(t===n||!this.isConnected)return;let i="data-sorted"===e&&this.hasAttribute("data-sorted");if(("data-updating"===e&&"eager"===n||i)&&this.update(),"aria-activedescendant"===e){let e=this.getIndexByElementId(n);this.dispatchEvent(new ActiveDescendantChangedEvent(e,n)),"eager"===this.updating&&this.update()}}connectedCallback(){this.addEventListener("scroll",()=>this.update()),this.updateSync=this.updateSync.bind(this),eE.observe(this)}update(){ew(this,eS)&&cancelAnimationFrame(ew(this,eS)),!ew(this,ex)&&this.hasAttribute("data-sorted")?ey(this,eS,requestAnimationFrame(()=>{this.dispatchEvent(new CustomEvent("virtual-list-sort",{cancelable:!0}))&&this.sort()})):ey(this,eS,requestAnimationFrame(this.updateSync))}renderItem(e){let t={item:e,fragment:document.createDocumentFragment()};return this.dispatchEvent(new CustomEvent("virtual-list-render-item",{detail:t})),t.fragment.children[0]}recalculateHeights(e){let t=this.list;if(!t)return;let n=this.renderItem(e);if(!n)return;t.append(n);let i=t.children[0].getBoundingClientRect().height;t.replaceChildren(),i&&(ey(this,eT,i),ew(this,eL).set(e,i))}getIndexByElementId(e){if(!e)return -1;let t=0;for(let[,n]of ew(this,e_)){if(n.id===e||n.querySelector(`#${e}`))return t;t++}return -1}updateSync(){let e=this.list,[t,n]=this.range;if(n<t)return;let i=!this.dispatchEvent(new CustomEvent("virtual-list-update",{cancelable:!0}));if(i)return;let r=new Map,s=ew(this,e_),a=-1,o=!0,l=0,u=0,d=0;for(let e of ew(this,eC)){if(-1!==a||Number.isFinite(ew(this,eT))&&0!==ew(this,eT)||this.recalculateHeights(e),a+=1,d=ew(this,eL).get(e)||ew(this,eT),a<t){l+=d,u=l;continue}if(a>n){o=!1;break}let i=null;if(s.has(e))i=s.get(e);else{if(!(i=this.renderItem(e)))continue;i.querySelector("[aria-setsize]")?.setAttribute("aria-setsize",ew(this,eC).size.toString()),i.querySelector("[aria-posinset]")?.setAttribute("aria-posinset",(a+1).toString()),s.set(e,i)}i.querySelector("[tabindex]")?.setAttribute("data-scrolltop",u.toString()),u+=d,r.set(e,i)}e.replaceChildren(...r.values()),e.style.paddingTop=`${l}px`;let c=this.size*ew(this,eT);e.style.height=`${c||0}px`;let h=!1,m=this.getBoundingClientRect().bottom;for(let[e,t]of r){let{height:n,bottom:i}=t.getBoundingClientRect();h=h||i>=m,ew(this,eL).set(e,n)}let p=!o&&this.size>r.size;if(p&&!h)return ew(this,ek).delete(`${this.scrollTop}-${this.getBoundingClientRect().height}`),this.update();this.dispatchEvent(new RenderedEvent(s)),this.dispatchEvent(new CustomEvent("virtual-list-updated"))}resetRenderCache(){ey(this,e_,new Map)}has(e){return ew(this,eC).has(e)}add(e){return ew(this,eC).add(e),ey(this,ex,!1),Number.isFinite(ew(this,eT))||this.recalculateHeights(e),this.resetRenderCache(),this.dispatchEvent(new Event("virtual-list-data-updated")),"eager"===this.updating&&this.update(),this}delete(e){let t=ew(this,eC).delete(e);return ey(this,ex,!1),ew(this,eL).delete(e),this.resetRenderCache(),this.dispatchEvent(new Event("virtual-list-data-updated")),"eager"===this.updating&&this.update(),t}clear(){ew(this,eC).clear(),ew(this,eL).clear(),ey(this,eT,1/0),ey(this,ex,!0),this.resetRenderCache(),this.dispatchEvent(new Event("virtual-list-data-updated")),"eager"===this.updating&&this.update()}forEach(e,t){for(let n of this)e.call(t,n,n,this)}entries(){return ew(this,eC).entries()}values(){return ew(this,eC).values()}keys(){return ew(this,eC).keys()}[eM](){return ew(this,eC)[Symbol.iterator]()}sort(e){return ey(this,eC,new Set(Array.from(this).sort(e))),ey(this,ex,!0),this.dispatchEvent(new Event("virtual-list-data-updated")),"eager"===this.updating&&this.update(),this}constructor(...e){super(...e),eb(this,ex,{writable:!0,value:!1}),eb(this,eC,{writable:!0,value:new Set}),eb(this,eL,{writable:!0,value:new Map}),eb(this,eT,{writable:!0,value:1/0}),eb(this,ek,{writable:!0,value:new Map}),eb(this,e_,{writable:!0,value:new Map}),eb(this,eS,{writable:!0,value:0})}};let ActiveDescendantChangedEvent=class ActiveDescendantChangedEvent extends Event{constructor(e,t){super("virtual-list-activedescendant-changed"),this.index=e,this.id=t}};let RenderedEvent=class RenderedEvent extends Event{constructor(e){super("virtual-list-rendered"),this.rowsCache=e}};window.customElements.get("virtual-list")||(window.VirtualListElement=eA,window.customElements.define("virtual-list",eA));var eq=function(e,t,n,i){var r,s=arguments.length,a=s<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,n):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,n,i);else for(var o=e.length-1;o>=0;o--)(r=e[o])&&(a=(s<3?r(a):s>3?r(t,n,a):r(t,n))||a);return s>3&&a&&Object.defineProperty(t,n,a),a};let eI=class VisiblePasswordElement extends HTMLElement{show(){this.input.type="text",this.input.focus(),this.showButton.hidden=!0,this.hideButton.hidden=!1}hide(){this.input.type="password",this.input.focus(),this.hideButton.hidden=!0,this.showButton.hidden=!1}};eq([g.fA],eI.prototype,"input",void 0),eq([g.fA],eI.prototype,"showButton",void 0),eq([g.fA],eI.prototype,"hideButton",void 0),eI=eq([g.Ih],eI);var eR=n(22490),eP=n(7180);let eN="include-fragment-element-no-op",eO=eR.Z.createPolicy(eN,{createHTML:e=>eP.O.apply({policy:()=>e,policyName:eN,fallback:e,fallbackOnError:!0})});window.IncludeFragmentElement.setCSPTrustedTypesPolicy(eO)},81775:(e,t,n)=>{n.d(t,{G:()=>u});var i=n(254),r=n(36071),s=n(59753);function a(e){let t=e.getAttribute("data-required-value"),n=e.getAttribute("data-required-value-prefix");if(e.value===t)e.setCustomValidity("");else{let i=t;n&&(i=n+i),e.setCustomValidity(i)}}(0,i.q6)("[data-required-value]",function(e){let t=e.currentTarget;a(t)}),(0,s.on)("change","[data-required-value]",function(e){let t=e.currentTarget;a(t),u(t.form)}),(0,i.q6)("[data-required-trimmed]",function(e){let t=e.currentTarget;""===t.value.trim()?t.setCustomValidity(t.getAttribute("data-required-trimmed")):t.setCustomValidity("")}),(0,s.on)("change","[data-required-trimmed]",function(e){let t=e.currentTarget;""===t.value.trim()?t.setCustomValidity(t.getAttribute("data-required-trimmed")):t.setCustomValidity(""),u(t.form)}),(0,i.ZG)("input[pattern],input[required],textarea[required],input[data-required-change],textarea[data-required-change],input[data-required-value],textarea[data-required-value]",e=>{let t=e.checkValidity();function n(){let n=e.checkValidity();n!==t&&e.form&&u(e.form),t=n}e.addEventListener("input",n),e.addEventListener("blur",function t(){e.removeEventListener("input",n),e.removeEventListener("blur",t)})});let o=new WeakMap;function l(e){o.get(e)||(e.addEventListener("change",()=>u(e)),o.set(e,!0))}function u(e){let t=e.checkValidity();for(let n of e.querySelectorAll("button[data-disable-invalid]"))n.disabled=!t}(0,r.N7)("button[data-disable-invalid]",{constructor:HTMLButtonElement,initialize(e){let t=e.form;t&&(l(t),e.disabled=!t.checkValidity())}}),(0,r.N7)("input[data-required-change], textarea[data-required-change]",function(e){let t="radio"===e.type&&e.form?e.form.elements.namedItem(e.name).value:null;function n(n){let i=e.form;if(n&&"radio"===e.type&&i&&t)for(let n of i.elements.namedItem(e.name))n instanceof HTMLInputElement&&n.setCustomValidity(e.value===t?"unchanged":"");else e.setCustomValidity(e.value===(t||e.defaultValue)?"unchanged":"")}e.addEventListener("input",n),e.addEventListener("change",n),n(),e.form&&u(e.form)}),document.addEventListener("reset",function(e){if(e.target instanceof HTMLFormElement){let t=e.target;setTimeout(()=>u(t))}})},97895:(e,t,n)=>{n.d(t,{Z:()=>c});var i=n(47142);let r=(e,t,n)=>{if(!(0,i.CD)(e,t))return-1/0;let r=(0,i.Gs)(e,t);return r<n?-1/0:r},s=(e,t,n)=>{e.textContent="";let r=0;for(let s of(0,i.m7)(t,n)){let t=n.slice(r,s);""!==t&&e.appendChild(document.createTextNode(n.slice(r,s))),r=s+1;let i=document.createElement("mark");i.textContent=n[s],e.appendChild(i)}e.appendChild(document.createTextNode(n.slice(r)))},a=new WeakMap,o=new WeakMap,l=new WeakMap,u=e=>{if(!l.has(e)&&e instanceof HTMLElement){let t=(e.getAttribute("data-value")||e.textContent||"").trim();return l.set(e,t),t}return l.get(e)||""},d=class FuzzyListElement extends HTMLElement{connectedCallback(){let e=this.querySelector("ul");if(!e)return;let t=new Set(e.querySelectorAll("li")),n=this.querySelector("input");n instanceof HTMLInputElement&&n.addEventListener("input",()=>{this.value=n.value});let r=new MutationObserver(e=>{let n=!1;for(let r of e)if("childList"===r.type&&r.addedNodes.length){for(let e of r.addedNodes)if(e instanceof HTMLLIElement&&!t.has(e)){let r=u(e);n=n||(0,i.CD)(this.value,r),t.add(e)}}n&&this.sort()});r.observe(e,{childList:!0});let s={handler:r,items:t,lazyItems:new Map,timer:null};o.set(this,s)}disconnectedCallback(){let e=o.get(this);e&&(e.handler.disconnect(),o.delete(this))}addLazyItems(e,t){let n=o.get(this);if(!n)return;let{lazyItems:r}=n,{value:s}=this,a=!1;for(let n of e)r.set(n,t),a=a||Boolean(s)&&(0,i.CD)(s,n);a&&this.sort()}sort(){let e=a.get(this);e&&(e.aborted=!0);let t={aborted:!1};a.set(this,t);let{minScore:n,markSelector:i,maxMatches:d,value:c}=this,h=o.get(this);if(!h||!this.dispatchEvent(new CustomEvent("fuzzy-list-will-sort",{cancelable:!0,detail:c})))return;let{items:m,lazyItems:p}=h,f=this.hasAttribute("mark-selector"),g=this.querySelector("ul");if(!g)return;let v=[];if(c){for(let e of m){let t=u(e),i=r(c,t,n);i!==-1/0&&v.push({item:e,score:i})}for(let[e,t]of p){let i=r(c,e,n);i!==-1/0&&v.push({text:e,render:t,score:i})}v.sort((e,t)=>t.score-e.score).splice(d)}else{let e=v.length;for(let t of m){if(e>=d)break;v.push({item:t,score:1}),e+=1}for(let[t,n]of p){if(e>=d)break;v.push({text:t,render:n,score:1}),e+=1}}requestAnimationFrame(()=>{if(t.aborted)return;let e=g.querySelector('input[type="radio"]:checked');g.textContent="";let n=0,r=()=>{if(t.aborted)return;let a=Math.min(v.length,n+100),o=document.createDocumentFragment();for(let e=n;e<a;e+=1){let t=v[e],n=null;if("render"in t&&"text"in t){let{render:e,text:i}=t;n=e(i),m.add(n),l.set(n,i),p.delete(i)}else"item"in t&&(n=t.item);n instanceof HTMLElement&&(f&&s(i&&n.querySelector(i)||n,f?c:"",u(n)),o.appendChild(n))}n=a;let d=!1;if(e instanceof HTMLInputElement)for(let t of o.querySelectorAll('input[type="radio"]:checked'))t instanceof HTMLInputElement&&t.value!==e.value&&(t.checked=!1,d=!0);for(let e of o.querySelectorAll('button[tabindex="-1"]'))e.setAttribute("tabindex","0");if(g.appendChild(o),e&&d&&e.dispatchEvent(new Event("change",{bubbles:!0})),a<v.length)requestAnimationFrame(r);else{g.hidden=0===v.length;let e=this.querySelector("[data-fuzzy-list-show-on-empty]");e&&(e.hidden=v.length>0),this.dispatchEvent(new CustomEvent("fuzzy-list-sorted",{detail:v.length}))}};r()})}get value(){return this.getAttribute("value")||""}set value(e){this.setAttribute("value",e)}get markSelector(){return this.getAttribute("mark-selector")||""}set markSelector(e){e?this.setAttribute("mark-selector",e):this.removeAttribute("mark-selector")}get minScore(){return Number(this.getAttribute("min-score")||0)}set minScore(e){Number.isNaN(e)||this.setAttribute("min-score",String(e))}get maxMatches(){return Number(this.getAttribute("max-matches")||1/0)}set maxMatches(e){Number.isNaN(e)||this.setAttribute("max-matches",String(e))}static get observedAttributes(){return["value","mark-selector","min-score","max-matches"]}attributeChangedCallback(e,t,n){if(t===n)return;let i=o.get(this);i&&(i.timer&&window.clearTimeout(i.timer),i.timer=window.setTimeout(()=>this.sort(),100))}},c=d;window.customElements.get("fuzzy-list")||(window.FuzzyListElement=d,window.customElements.define("fuzzy-list",d))},254:(e,t,n)=>{n.d(t,{ZG:()=>o,q6:()=>u,w4:()=>l});var i=n(8439);let r=!1,s=new i.Z;function a(e){let t=e.target;if(t instanceof HTMLElement&&t.nodeType!==Node.DOCUMENT_NODE)for(let e of s.matches(t))e.data.call(null,t)}function o(e,t){r||(r=!0,document.addEventListener("focus",a,!0)),s.add(e,t),document.activeElement instanceof HTMLElement&&document.activeElement.matches(e)&&t(document.activeElement)}function l(e,t,n){function i(t){let r=t.currentTarget;r&&(r.removeEventListener(e,n),r.removeEventListener("blur",i))}o(t,function(t){t.addEventListener(e,n),t.addEventListener("blur",i)})}function u(e,t){function n(e){let{currentTarget:i}=e;i&&(i.removeEventListener("input",t),i.removeEventListener("blur",n))}o(e,function(e){e.addEventListener("input",t),e.addEventListener("blur",n)})}},87551:(e,t,n)=>{function i(){return/Windows/.test(navigator.userAgent)?"windows":/Macintosh/.test(navigator.userAgent)?"mac":null}function r(e){let t=(e.getAttribute("data-platforms")||"").split(","),n=i();return Boolean(n&&t.includes(n))}n.d(t,{X:()=>i}),(0,n(36071).N7)(".js-remove-unless-platform",function(e){r(e)||e.remove()})},89359:(e,t,n)=>{function i(e){let t=document.querySelectorAll(e);if(t.length>0)return t[t.length-1]}function r(){let e=i("meta[name=analytics-location]");return e?e.content:window.location.pathname}function s(){let e=i("meta[name=analytics-location-query-strip]"),t="";e||(t=window.location.search);let n=i("meta[name=analytics-location-params]");for(let e of(n&&(t+=(t?"&":"?")+n.content),document.querySelectorAll("meta[name=analytics-param-rename]"))){let n=e.content.split(":",2);t=t.replace(RegExp(`(^|[?&])${n[0]}($|=)`,"g"),`$1${n[1]}$2`)}return t}function a(){return`${window.location.protocol}//${window.location.host}${r()+s()}`}n.d(t,{S:()=>a})},24601:(e,t,n)=>{n.d(t,{aJ:()=>T,cI:()=>x,eK:()=>w});var i=n(82918),r=n(49237),s=n(28382),a=n(89359),o=n(68202),l=n(53729),u=n(86283),d=n(46426);let c=!1,h=0,m=Date.now(),p=new Set(["Failed to fetch","NetworkError when attempting to fetch resource."]);function f(e){return e instanceof Error||"object"==typeof e&&null!==e&&"name"in e&&"string"==typeof e.name&&"message"in e&&"string"==typeof e.message}function g(e){try{return JSON.stringify(e)}catch{return"Unserializable"}}function v(e){return!!("AbortError"===e.name||"TypeError"===e.name&&p.has(e.message)||e.name.startsWith("ApiError")&&p.has(e.message))}function w(e,t={}){if((0,d.c)("FAILBOT_HANDLE_NON_ERRORS")){if(!f(e)){if(M(e))return;let n=Error(),i=g(e),r={type:"UnknownError",value:`Unable to report error, due to a thrown non-Error type: ${typeof e}, with value ${i}`,stacktrace:x(n)};b(E(r,t));return}v(e)||b(E(y(e),t))}else v(e)||b(E(y(e),t))}async function b(e){if(!_())return;let t=document.head?.querySelector('meta[name="browser-errors-url"]')?.content;if(t){if(L(e.error.stacktrace)){c=!0;return}h++;try{await fetch(t,{method:"post",body:JSON.stringify(e)})}catch{}}}function y(e){return{type:e.name,value:e.message,stacktrace:x(e)}}function E(e,t={}){return Object.assign({error:e,sanitizedUrl:(0,a.S)()||window.location.href,readyState:document.readyState,referrer:(0,o.wP)(),timeSinceLoad:Math.round(Date.now()-m),user:T()||void 0,bundler:l.A7,ui:Boolean(document.querySelector('meta[name="ui"]'))},t)}function x(e){return(0,s.Q)(e.stack||"").map(e=>({filename:e.file||"",function:String(e.methodName),lineno:(e.lineNumber||0).toString(),colno:(e.column||0).toString()}))}let C=/(chrome|moz|safari)-extension:\/\//;function L(e){return e.some(e=>C.test(e.filename)||C.test(e.function))}function T(){let e=document.head?.querySelector('meta[name="user-login"]')?.content;if(e)return e;let t=(0,i.b)();return`anonymous-${t}`}let k=!1;function _(){return!k&&!c&&h<10&&(0,r.Gb)()}if(u.iG?.addEventListener("pageshow",()=>k=!1),u.iG?.addEventListener("pagehide",()=>k=!0),"function"==typeof BroadcastChannel){let e=new BroadcastChannel("shared-worker-error");e.addEventListener("message",e=>{w(e.data.error)})}let S=["Object Not Found Matching Id","Not implemented on this platform","provider because it's not your default extension"];function M(e){if(!e||"boolean"==typeof e||"number"==typeof e)return!0;if("string"==typeof e){if(S.some(t=>e.includes(t)))return!0}else if("object"==typeof e&&"string"==typeof e.message&&"number"==typeof e.code)return!0;return!1}},95253:(e,t,n)=>{let i;n.d(t,{Y:()=>h,q:()=>m});var r=n(88149),s=n(86058),a=n(44544),o=n(71643);let{getItem:l}=(0,a.Z)("localStorage"),u="dimension_",d=["utm_source","utm_medium","utm_campaign","utm_term","utm_content","scid"];try{let e=(0,r.n)("octolytics");delete e.baseContext,i=new s.R(e)}catch(e){}function c(e){let t=(0,r.n)("octolytics").baseContext||{};if(t)for(let[e,n]of(delete t.app_id,delete t.event_url,delete t.host,Object.entries(t)))e.startsWith(u)&&(t[e.replace(u,"")]=n,delete t[e]);let n=document.querySelector("meta[name=visitor-payload]");if(n){let e=JSON.parse(atob(n.content));Object.assign(t,e)}let i=new URLSearchParams(window.location.search);for(let[e,n]of i)d.includes(e.toLowerCase())&&(t[e]=n);return t.staff=(0,o.B)().toString(),Object.assign(t,e)}function h(e){i?.sendPageView(c(e))}function m(e,t={}){let n=document.head?.querySelector('meta[name="current-catalog-service"]')?.content,r=n?{service:n}:{};for(let[e,n]of Object.entries(t))null!=n&&(r[e]=`${n}`);i&&(c(r),i.sendEvent(e||"unknown",c(r)))}},7180:(e,t,n)=>{n.d(t,{O:()=>d,d:()=>TrustedTypesPolicyError});var i=n(46426),r=n(71643),s=n(24601),a=n(27856),o=n.n(a),l=n(95253);let TrustedTypesPolicyError=class TrustedTypesPolicyError extends Error{};function u({policy:e,policyName:t,fallback:n,fallbackOnError:a=!1,sanitize:u,silenceErrorReporting:d=!1}){try{if((0,i.c)("BYPASS_TRUSTED_TYPES_POLICY_RULES"))return n;(0,r.b)({incrementKey:"TRUSTED_TYPES_POLICY_CALLED",trustedTypesPolicyName:t},!1,.1);let s=e();return u&&new Promise(e=>{let n=window.performance.now(),i=o().sanitize(s,{FORBID_ATTR:[]}),r=window.performance.now();if(s.length!==i.length){let a=Error("Trusted Types policy output sanitized"),o=a.stack?.slice(0,1e3),u=s.slice(0,250);(0,l.q)("trusted_types_policy.sanitize",{policyName:t,output:u,stack:o,outputLength:s.length,sanitizedLength:i.length,executionTime:r-n}),e(s)}}),s}catch(e){if(e instanceof TrustedTypesPolicyError||(d||(0,s.eK)(e),(0,r.b)({incrementKey:"TRUSTED_TYPES_POLICY_ERROR",trustedTypesPolicyName:t}),!a))throw e}return n}let d={apply:u}},22490:(e,t,n)=>{n.d(t,{Z:()=>o});var i=n(86283);function r(e){return()=>{throw TypeError(`The policy does not implement the function ${e}`)}}let s={createHTML:r("createHTML"),createScript:r("createScript"),createScriptURL:r("createScriptURL")},a={createPolicy:(e,t)=>({name:e,...s,...t})},o=globalThis.trustedTypes??a,l=!1;i.n4?.addEventListener("securitypolicyviolation",e=>{"require-trusted-types-for"!==e.violatedDirective||l||(console.warn(`Hi fellow Hubber!
    You're probably seeing a Report Only Trusted Types error near this message. This is intended behaviour, staff-only,
    does not impact application control flow, and is used solely for statistic collection. Unfortunately we
    can't gather these statistics without adding the above warnings to your console. Sorry about that!
    Feel free to drop by #pse-architecture if you have any additional questions about Trusted Types or CSP.`),l=!0)})}},e=>{var t=t=>e(e.s=t);e.O(0,["vendors-node_modules_dompurify_dist_purify_js","vendors-node_modules_stacktrace-parser_dist_stack-trace-parser_esm_js-node_modules_github_bro-a4c183","vendors-node_modules_github_selector-observer_dist_index_esm_js","vendors-node_modules_primer_behaviors_dist_esm_focus-zone_js","vendors-node_modules_github_relative-time-element_dist_index_js","vendors-node_modules_delegated-events_dist_index_js-node_modules_github_auto-complete-element-5b3870","vendors-node_modules_github_filter-input-element_dist_index_js-node_modules_github_remote-inp-b7d8f4","vendors-node_modules_github_file-attachment-element_dist_index_js-node_modules_primer_view-co-821777","ui_packages_soft-nav_soft-nav_ts"],()=>t(10361));var n=e.O()}]);
//# sourceMappingURL=github-elements-7681e569c8a6.js.map