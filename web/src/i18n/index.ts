import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import bn from './bn.json'
import en from './en.json'
import hi from './hi.json'
import ta from './ta.json'
import te from './te.json'

const resources = { en, hi, te, ta, bn }
const browser = navigator.language.slice(0, 2)
const lng = browser in resources ? browser : 'en'

// tokens.css sets the taller line height for Indian scripts from :lang()
document.documentElement.lang = lng

i18n.use(initReactI18next).init({
  resources: Object.fromEntries(Object.entries(resources).map(([k, v]) => [k, { translation: v }])),
  lng,
  interpolation: { escapeValue: false },
})
