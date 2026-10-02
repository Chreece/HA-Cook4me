import './cook4me-panel-v180.js?productmobile=269';
import {MobileProductMixin} from './mobile-product-v269.js';

const ELEMENT='cook4me-recipe-hub-panel-v180-runtime-v269';
const Previous=customElements.get('cook4me-recipe-hub-panel-v180-runtime-v268');
if(!customElements.get(ELEMENT))customElements.define(ELEMENT,MobileProductMixin(Previous));
