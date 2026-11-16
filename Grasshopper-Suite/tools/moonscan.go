package main

import (
	"bufio"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"html"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	appName    = "MoonScan"
	appTitle = "MoonScan"
	appVersion = "1.0.0"
)

const (
	cRed    = "239;68;68"
	cGreen  = "74;222;128"
	cCyan   = "34;211;238"
	cYellow = "250;204;21"
	cGray   = "148;163;184"
	cWhite  = "241;245;249"
)

var useColor = true

var bannerLines = []string{
	"███▄ ▄███▓ ▒█████   ▒█████   ███▄    █   ██████  ▄████▄   ▄▄▄       ███▄    █",
	"▓██▒▀█▀ ██▒▒██▒  ██▒▒██▒  ██▒ ██ ▀█   █ ▒██    ▒ ▒██▀ ▀█  ▒████▄     ██ ▀█   █",
	"▓██    ▓██░▒██░  ██▒▒██░  ██▒▓██  ▀█ ██▒░ ▓██▄   ▒▓█    ▄ ▒██  ▀█▄  ▓██  ▀█ ██▒",
	"▒██    ▒██ ▒██   ██░▒██   ██░▓██▒  ▐▌██▒  ▒   ██▒▒▓▓▄ ▄██▒░██▄▄▄▄██ ▓██▒  ▐▌██▒",
	"▒██▒   ░██▒░ ████▓▒░░ ████▓▒░▒██░   ▓██░▒██████▒▒▒ ▓███▀ ░ ▓█   ▓██▒▒██░   ▓██░",
	"░ ▒░   ░  ░░ ▒░▒░▒░ ░ ▒░▒░▒░ ░ ▒░   ▒ ▒ ▒ ▒▓▒ ▒ ░░ ░▒ ▒  ░ ▒▒   ▓▒█░░ ▒░   ▒ ▒",
	"░  ░      ░  ░ ▒ ▒░   ░ ▒ ▒░ ░ ░░   ░ ▒░░ ░▒  ░ ░  ░  ▒     ▒   ▒▒ ░░ ░░   ░ ▒░",
	"░      ░   ░ ░ ░ ▒  ░ ░ ░ ▒     ░   ░ ░ ░  ░  ░  ░          ░   ▒      ░   ░ ░",
	"       ░       ░ ░      ░ ░           ░       ░  ░ ░            ░  ░         ░",
	"                                                 ░",
}

type Config struct {
	Verbose     bool
	Deep        bool
	Insecure    bool
	NoGeo       bool
	NoReport    bool
	NoColor     bool
	ForceColor  bool
	NoBanner    bool
	Follow      bool
	JSON        bool
	Help        bool
	Version     bool
	ListTechs   bool
	Interactive bool
	Threads     int
	Timeout     time.Duration
	Agent       string
	Proxy       string
	Cookie      string
	Headers     []string
	Output      string
	List        string
}

func defaultConfig() *Config {
	return &Config{
		Follow:  true,
		Threads: 5,
		Timeout: 12 * time.Second,
		Agent:   "Mozilla/5.0 (Linux; Android 14; Termux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36 MoonScan/" + appVersion,
	}
}

type Tech struct {
	Name     string   `json:"nome"`
	Cat      string   `json:"categoria"`
	Version  string   `json:"versao,omitempty"`
	Conf     int      `json:"confianca"`
	Inferred bool     `json:"inferido,omitempty"`
	Evidence []string `json:"evidencias,omitempty"`
}

type Finding struct {
	Sev    string `json:"severidade"`
	Title  string `json:"titulo"`
	Detail string `json:"detalhe,omitempty"`
}

type Result struct {
	Target       string    `json:"alvo"`
	FinalURL     string    `json:"url_final,omitempty"`
	IP           string    `json:"ip,omitempty"`
	Geo          string    `json:"geolocalizacao,omitempty"`
	Status       int       `json:"status_http,omitempty"`
	Proto        string    `json:"protocolo,omitempty"`
	TimeMs       int64     `json:"tempo_ms,omitempty"`
	Title        string    `json:"titulo,omitempty"`
	Server       string    `json:"servidor,omitempty"`
	PoweredBy    string    `json:"powered_by,omitempty"`
	OS           string    `json:"sistema_operacional,omitempty"`
	WAF          []string  `json:"waf,omitempty"`
	TLS          string    `json:"tls,omitempty"`
	Cert         string    `json:"certificado,omitempty"`
	Redirects    []string  `json:"redirecionamentos,omitempty"`
	Cookies      []string  `json:"cookies,omitempty"`
	Emails       []string  `json:"emails,omitempty"`
	Files        []string  `json:"arquivos,omitempty"`
	ExtraHeaders []string  `json:"headers_incomuns,omitempty"`
	Techs        []*Tech   `json:"tecnologias"`
	Findings     []Finding `json:"achados"`
	Deep         bool      `json:"modo_deep"`
	Error        string    `json:"erro,omitempty"`
	Date         string    `json:"data"`
}

type page struct {
	URL     string
	Status  int
	Proto   string
	Header  http.Header
	HL      map[string]string
	Body    string
	TLS     *tls.ConnectionState
	Chain   []string
	Cookies []*http.Cookie
	Dur     time.Duration
}

type assets struct {
	refs    string
	scripts []string
	cookies string
	meta    map[string]string
}

type rule struct {
	tech   string
	cat    string
	src    string
	path   string
	weight int
	re     *regexp.Regexp
}

type imp struct {
	name string
	cat  string
	conf int
}

var (
	rules     []rule
	techCount int
	catCount  int
	badRules  int
)

var (
	reScript   = regexp.MustCompile(`(?is)<script[^>]+src\s*=\s*["']([^"']+)["']`)
	reLink     = regexp.MustCompile(`(?is)<link[^>]+href\s*=\s*["']([^"']+)["']`)
	reMeta     = regexp.MustCompile(`(?is)<meta\s[^>]*>`)
	reMetaKey  = regexp.MustCompile(`(?is)(?:name|property|http-equiv)\s*=\s*["']([^"']+)["']`)
	reMetaVal  = regexp.MustCompile(`(?is)content\s*=\s*["']([^"']*)["']`)
	reTitle    = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)
	reEmail    = regexp.MustCompile(`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`)
	reSpace    = regexp.MustCompile(`\s+`)
	rePass     = regexp.MustCompile(`(?i)<input[^>]+type\s*=\s*["']?password`)
	reWeakCSP  = regexp.MustCompile(`(?i)unsafe-inline|unsafe-eval|(?:default|script)-src[^;]*\s\*(?:\s|;|$)`)
	reVerShow  = regexp.MustCompile(`\d+\.\d+`)
	reHSTSAge  = regexp.MustCompile(`(?i)max-age\s*=\s*"?(\d+)`)
	badMailExt = map[string]bool{"png": true, "jpg": true, "jpeg": true, "gif": true, "webp": true, "svg": true, "js": true, "css": true, "ico": true, "woff": true, "woff2": true}
)

var wafAlso = map[string]bool{"Cloudflare": true, "Akamai": true}

var commonHeaders = map[string]bool{
	"date": true, "content-type": true, "content-length": true, "connection": true, "server": true,
	"cache-control": true, "etag": true, "last-modified": true, "expires": true, "vary": true,
	"content-encoding": true, "set-cookie": true, "location": true, "accept-ranges": true, "pragma": true,
	"age": true, "via": true, "x-powered-by": true, "strict-transport-security": true, "x-frame-options": true,
	"content-security-policy": true, "x-content-type-options": true, "referrer-policy": true,
	"permissions-policy": true, "x-xss-protection": true, "transfer-encoding": true, "keep-alive": true,
	"alt-svc": true, "link": true, "access-control-allow-origin": true,
}

var stackOrder = []struct {
	cat   string
	label string
	core  bool
}{
	{"CMS", "CMS", true},
	{"E-commerce", "E-commerce", false},
	{"Builder", "Builder", false},
	{"Framework", "Framework", true},
	{"Language", "Language", true},
	{"Server", "Web Server", false},
	{"JavaScript", "JavaScript", true},
	{"UI", "UI/CSS", false},
	{"Plugin", "Plugins", false},
	{"Database", "Database", true},
	{"CDN", "CDN", true},
	{"Hosting", "Hosting", false},
	{"Cache", "Cache", false},
	{"Analytics", "Analytics", false},
	{"Third-party", "Third-party", false},
	{"Fonts", "Fonts", false},
	{"Markup", "Markup", false},
}

var implies = map[string][]imp{
	"WordPress":     {{"PHP", "Language", 75}, {"MySQL/MariaDB", "Database", 55}},
	"WooCommerce":   {{"WordPress", "CMS", 70}},
	"Elementor":     {{"WordPress", "CMS", 70}},
	"Yoast SEO":     {{"WordPress", "CMS", 70}},
	"Contact Form 7": {{"WordPress", "CMS", 70}},
	"WPBakery":      {{"WordPress", "CMS", 70}},
	"Divi":          {{"WordPress", "CMS", 70}},
	"Joomla":        {{"PHP", "Language", 75}, {"MySQL/MariaDB", "Database", 55}},
	"Drupal":        {{"PHP", "Language", 75}, {"MySQL/MariaDB", "Database", 50}},
	"Magento":       {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 60}},
	"PrestaShop":    {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 60}},
	"OpenCart":      {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 60}},
	"TYPO3":         {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 55}},
	"MediaWiki":     {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 55}},
	"phpBB":         {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 55}},
	"Moodle":        {{"PHP", "Language", 80}, {"MySQL/MariaDB", "Database", 55}},
	"Laravel":       {{"PHP", "Language", 85}},
	"Symfony":       {{"PHP", "Language", 85}},
	"CodeIgniter":   {{"PHP", "Language", 85}},
	"CakePHP":       {{"PHP", "Language", 85}},
	"Django":        {{"Python", "Language", 85}},
	"Gunicorn":      {{"Python", "Language", 80}},
	"Werkzeug":      {{"Python", "Language", 80}},
	"Uvicorn":       {{"Python", "Language", 80}},
	"Ruby on Rails": {{"Ruby", "Language", 85}},
	"Puma":          {{"Ruby", "Language", 75}},
	"Express":       {{"Node.js", "Language", 70}},
	"Next.js":       {{"React", "JavaScript", 85}, {"Node.js", "Language", 60}},
	"Nuxt.js":       {{"Vue.js", "JavaScript", 85}, {"Node.js", "Language", 60}},
	"Gatsby":        {{"React", "JavaScript", 85}},
	"Remix":         {{"React", "JavaScript", 85}},
	"Docusaurus":    {{"React", "JavaScript", 80}},
	"Strapi":        {{"Node.js", "Language", 80}},
	"Ghost":         {{"Node.js", "Language", 70}},
	"Apache Tomcat": {{"Java", "Language", 80}},
	"Jetty":         {{"Java", "Language", 80}},
}

const sigDB = `
Nginx~Server~h:server~100~nginx(?:/([\d.]+))?
Nginx~Server~body~40~<center>nginx</center>
Apache~Server~h:server~100~apache(?:/([\d.]+))?(?:\s|$|\()
Apache Tomcat~Server~h:server~100~apache-coyote|tomcat(?:/([\d.]+))?
LiteSpeed~Server~h:server~100~litespeed
OpenResty~Server~h:server~100~openresty(?:/([\d.]+))?
Microsoft IIS~Server~h:server~100~microsoft-iis(?:/([\d.]+))?
lighttpd~Server~h:server~100~lighttpd(?:/([\d.]+))?
Caddy~Server~h:server~100~caddy
Envoy~Server~h:server~100~envoy
Gunicorn~Server~h:server~100~gunicorn(?:/([\d.]+))?
Uvicorn~Server~h:server~100~uvicorn
Werkzeug~Server~h:server~100~werkzeug(?:/([\d.]+))?
Kestrel~Server~h:server~100~kestrel
Jetty~Server~h:server~100~jetty(?:[/(]([\d.]+))?
Puma~Server~h:server~100~puma
Cowboy~Server~h:server~100~cowboy
Phusion Passenger~Server~h:x-powered-by~100~passenger(?: ([\d.]+))?
Phusion Passenger~Server~h:server~100~passenger(?: ([\d.]+))?
Varnish~Cache~h:via~100~varnish
Varnish~Cache~h:x-varnish~100~.
Squid~Cache~h:via~80~squid(?:/([\d.]+))?
PHP~Language~h:x-powered-by~100~php(?:/([\d.]+))?
PHP~Language~h:server~90~php(?:/([\d.]+))?
PHP~Language~cookie~60~phpsessid
PHP~Language~url~40~\.php(?:$|\?)
Python~Language~h:server~70~python(?:/([\d.]+))?
Python~Language~h:x-powered-by~70~python(?:/([\d.]+))?
Java~Language~cookie~60~jsessionid
Java~Language~h:x-powered-by~80~servlet|jsp
Ruby~Language~h:server~70~ruby(?:/([\d.]+))?
ASP.NET~Framework~h:x-powered-by~100~asp\.net
ASP.NET~Framework~h:x-aspnet-version~100~([\d.]+)
ASP.NET~Framework~h:x-aspnetmvc-version~100~([\d.]+)
ASP.NET~Framework~cookie~70~asp\.net_sessionid|\.aspxauth
ASP.NET~Framework~body~50~__viewstate|__eventvalidation
Ruby on Rails~Framework~meta:csrf-param~60~authenticity_token
Ruby on Rails~Framework~body~50~name="authenticity_token"
Ruby on Rails~Framework~h:x-runtime~30~^[\d.]+$
Django~Framework~cookie~70~csrftoken
Django~Framework~body~70~csrfmiddlewaretoken
Laravel~Framework~cookie~90~laravel_session
Laravel~Framework~cookie~30~xsrf-token
Symfony~Framework~h:x-debug-token~100~.
CodeIgniter~Framework~cookie~80~ci_session
CakePHP~Framework~cookie~80~cakephp
Express~Framework~h:x-powered-by~100~express
Spring~Framework~h:x-application-context~100~.
Next.js~Framework~h:x-powered-by~100~next\.js(?: ([\d.]+))?
Next.js~Framework~body~90~/_next/static/|__next_data__
Nuxt.js~Framework~body~90~/_nuxt/|window\.__nuxt__
Gatsby~Framework~meta:generator~100~gatsby(?: ([\d.]+))?
Gatsby~Framework~body~70~___gatsby|/page-data/
SvelteKit~Framework~body~80~/_app/immutable/|__sveltekit
Astro~Framework~meta:generator~100~astro v?([\d.]+)?
Astro~Framework~body~80~<astro-island|data-astro-cid
Remix~Framework~body~80~__remixcontext
WordPress~CMS~meta:generator~100~wordpress(?: ([\d.]+))?
WordPress~CMS~body~75~/wp-content/|/wp-includes/
WordPress~CMS~h:link~90~api\.w\.org
WordPress~CMS~h:x-pingback~60~xmlrpc\.php
WordPress~CMS~body~40~wp-emoji-release\.min\.js|wp-json
Joomla~CMS~meta:generator~100~joomla!?(?: ([\d.]+))?
Joomla~CMS~body~60~/media/jui/|/components/com_|/media/system/js/
Drupal~CMS~meta:generator~100~drupal(?: ([\d.]+))?
Drupal~CMS~h:x-generator~100~drupal(?: ([\d.]+))?
Drupal~CMS~h:x-drupal-cache~100~.
Drupal~CMS~h:x-drupal-dynamic-cache~100~.
Drupal~CMS~body~70~drupal\.settings|/sites/default/files|data-drupal-selector
Ghost~CMS~meta:generator~100~ghost(?: ([\d.]+))?
TYPO3~CMS~meta:generator~100~typo3
TYPO3~CMS~body~70~typo3conf/|typo3temp/
Strapi~CMS~h:x-powered-by~100~strapi
Blogger~CMS~meta:generator~100~blogger
Hugo~CMS~meta:generator~100~hugo(?: ([\d.]+))?
Jekyll~CMS~meta:generator~100~jekyll(?: v?([\d.]+))?
Hexo~CMS~meta:generator~100~hexo(?: ([\d.]+))?
Docusaurus~CMS~meta:generator~100~docusaurus(?: v?([\d.]+))?
MkDocs~CMS~meta:generator~100~mkdocs(?:-([\d.]+))?
MediaWiki~CMS~meta:generator~100~mediawiki(?: ([\d.]+))?
Discourse~CMS~meta:generator~100~discourse
phpBB~CMS~cookie~70~phpbb3_
vBulletin~CMS~meta:generator~100~vbulletin(?: ([\d.]+))?
Moodle~CMS~cookie~80~moodlesession
Moodle~CMS~body~50~moodle
Confluence~CMS~meta:ajs-version-number~100~([\d.]+)
Magento~E-commerce~body~70~/static/(?:version\d+/)?frontend/|mage/cookies|magento_ui
Magento~E-commerce~cookie~60~mage-cache|frontend_cid
Shopify~E-commerce~h:x-shopid~100~.
Shopify~E-commerce~body~90~cdn\.shopify\.com|shopify\.theme
Shopify~E-commerce~cookie~60~_shopify_
WooCommerce~E-commerce~meta:generator~100~woocommerce(?: ([\d.]+))?
WooCommerce~E-commerce~body~85~woocommerce
PrestaShop~E-commerce~meta:generator~100~prestashop
PrestaShop~E-commerce~body~60~/modules/ps_|prestashop
OpenCart~E-commerce~body~70~catalog/view/(?:theme|javascript)
BigCommerce~E-commerce~body~80~cdn\d*\.bigcommerce\.com
Nuvemshop~E-commerce~body~80~nuvemshop|tiendanube
VTEX~E-commerce~body~80~vteximg\.com\.br|vtexassets\.com|vtex\.com\.br
Loja Integrada~E-commerce~body~80~lojaintegrada\.com\.br
Wix~Builder~meta:generator~100~wix\.com
Wix~Builder~h:x-wix-request-id~100~.
Wix~Builder~body~80~static\.parastorage\.com|wixstatic\.com
Squarespace~Builder~meta:generator~100~squarespace
Squarespace~Builder~body~85~static1?\.squarespace\.com|squarespace-cdn
Webflow~Builder~meta:generator~100~webflow
Webflow~Builder~body~70~data-wf-page|data-wf-site
Webpack~Builder~body~60~webpackjsonp|webpackchunk|__webpack_require__
Vite~Builder~script~60~/@vite/client|/assets/index-[\w-]{8}\.js
Elementor~Plugin~meta:generator~100~elementor ([\d.]+)
Elementor~Plugin~body~70~elementor-(?:element|section|widget)|/plugins/elementor/
Yoast SEO~Plugin~body~100~yoast seo plugin v?([\d.]+)?
Contact Form 7~Plugin~body~80~wpcf7|/contact-form-7/
WPBakery~Plugin~body~70~js_composer|wpb_(?:row|column)
Divi~Plugin~body~80~et-boc|/themes/divi/|et_pb_
Slider Revolution~Plugin~body~80~revslider|rs-plugin
jQuery~JavaScript~script~70~(?:^|/)jquery(?:[-.]min)?\.js
jQuery~JavaScript~script~100~(?:^|/)jquery[-.@/]v?(\d+\.\d+(?:\.\d+)?)
jQuery~JavaScript~script~100~(?:^|/)jquery(?:\.min)?\.js\?ver=(\d+\.\d+(?:\.\d+)?)
jQuery~JavaScript~body~80~jquery (?:javascript library )?v(\d+\.\d+(?:\.\d+)?)
jQuery UI~JavaScript~script~100~(?:^|/)jquery[-.]?ui(?:[-.@/]v?(\d+\.\d+(?:\.\d+)?))?
jQuery Migrate~JavaScript~script~100~jquery[-.]migrate(?:[-.@/]v?(\d+\.\d+(?:\.\d+)?))?
React~JavaScript~script~80~(?:^|/)react(?:-dom)?(?:\.production|\.development)?(?:\.min)?\.js
React~JavaScript~script~100~react(?:-dom)?[@/-]v?(\d+\.\d+\.\d+)
React~JavaScript~body~70~data-reactroot|data-reactid|__react_devtools_global_hook__
Vue.js~JavaScript~script~80~(?:^|/)vue(?:\.runtime)?(?:\.global)?(?:\.prod)?(?:\.esm-browser)?(?:\.min)?\.js
Vue.js~JavaScript~script~100~(?:^|/)vue(?:@|/|-)v?(\d+\.\d+\.\d+)
Vue.js~JavaScript~body~50~data-v-[0-9a-f]{8}|data-server-rendered="true"
AngularJS~JavaScript~script~90~(?:^|/)angular(?:\.min)?\.js
AngularJS~JavaScript~script~100~angular(?:\.js)?[@/-]v?(1\.\d+\.\d+)
AngularJS~JavaScript~body~70~ng-app=|ng-controller=
Angular~JavaScript~body~90~ng-version="([\d.]+)"
Lodash~JavaScript~script~80~(?:^|/)lodash(?:\.min)?\.js
Lodash~JavaScript~script~100~lodash(?:\.js)?[@/-]v?(\d+\.\d+\.\d+)
Lodash~JavaScript~body~100~lodash (\d+\.\d+\.\d+)
Moment.js~JavaScript~script~80~(?:^|/)moment(?:\.min)?\.js|moment-with-locales
Moment.js~JavaScript~script~100~moment(?:\.js)?[@/-]v?(\d+\.\d+\.\d+)
Underscore.js~JavaScript~script~80~(?:^|/)underscore(?:-min|\.min)?\.js
Underscore.js~JavaScript~script~100~underscore(?:\.js)?[@/-]v?(\d+\.\d+\.\d+)
Axios~JavaScript~script~80~(?:^|/)axios(?:\.min)?\.js
Axios~JavaScript~script~100~axios[@/-]v?(\d+\.\d+\.\d+)
Handlebars~JavaScript~script~80~handlebars(?:\.min|\.runtime)*\.js
Handlebars~JavaScript~script~100~handlebars(?:\.js)?[@/-]v?(\d+\.\d+\.\d+)
D3.js~JavaScript~script~90~(?:^|/)d3(?:\.v\d+)?(?:\.min)?\.js
Three.js~JavaScript~script~90~(?:^|/)three(?:\.module)?(?:\.min)?\.js
Chart.js~JavaScript~script~90~(?:^|/)chart(?:\.umd)?(?:\.min)?\.js
Chart.js~JavaScript~script~100~chart\.js[@/]v?(\d+\.\d+\.\d+)
GSAP~JavaScript~script~90~gsap(?:\.min)?\.js|/gsap/
Alpine.js~JavaScript~script~90~alpine(?:\.min)?\.js|alpinejs
Alpine.js~JavaScript~body~50~x-data=|x-init=
htmx~JavaScript~script~90~htmx(?:\.min)?\.js
htmx~JavaScript~body~50~hx-(?:get|post|swap|target)=
Socket.IO~JavaScript~script~90~socket\.io(?:\.min)?\.js|/socket\.io/
Swiper~JavaScript~script~85~swiper(?:-bundle)?(?:\.min)?\.(?:js|css)
Leaflet~JavaScript~script~90~leaflet(?:\.min)?\.(?:js|css)
Select2~JavaScript~script~85~select2(?:\.min|\.full)*\.js
DataTables~JavaScript~script~85~datatables(?:\.min)?\.js|jquery\.datatables
Modernizr~JavaScript~script~90~modernizr
Backbone.js~JavaScript~script~90~backbone(?:-min|\.min)?\.js
Ember.js~JavaScript~script~90~ember(?:\.prod|\.min)*\.js
Bootstrap~UI~script~80~(?:^|/)bootstrap(?:[.-]bundle)?(?:\.min)?\.(?:js|css)
Bootstrap~UI~script~100~bootstrap[@/-]v?(\d+\.\d+\.\d+)
Bootstrap~UI~body~100~bootstrap v(\d+\.\d+\.\d+)
Bootstrap~UI~body~50~class="[^"]*\b(?:container-fluid|col-(?:xs|sm|md|lg)-\d+|navbar-expand)\b
Tailwind CSS~UI~body~80~cdn\.tailwindcss\.com|tailwindcss
Bulma~UI~script~80~bulma(?:\.min)?\.css
Font Awesome~Fonts~script~85~font-?awesome(?:[@/-]v?(\d+\.\d+\.\d+))?
Google Fonts~Fonts~script~100~fonts\.googleapis\.com
Google Analytics~Analytics~body~100~googletagmanager\.com/gtag/js\?id=((?:G|UA|AW)-[\w-]+)
Google Analytics~Analytics~body~100~google-analytics\.com/(?:analytics|ga)\.js
Google Analytics~Analytics~body~90~['"](UA-\d{4,10}-\d{1,3})['"]
Google Tag Manager~Analytics~body~100~googletagmanager\.com/gtm\.js\?id=(GTM-\w+)
Google Tag Manager~Analytics~body~70~googletagmanager\.com/ns\.html\?id=(GTM-\w+)
Facebook Pixel~Analytics~body~100~connect\.facebook\.net/[\w_]+/fbevents\.js
TikTok Pixel~Analytics~body~100~analytics\.tiktok\.com
Hotjar~Analytics~body~100~static\.hotjar\.com
Microsoft Clarity~Analytics~body~100~clarity\.ms/tag
Matomo~Analytics~body~90~matomo\.js|piwik\.js|/matomo\.php
Plausible~Analytics~body~100~plausible\.io/js
Cloudflare Web Analytics~Analytics~body~100~static\.cloudflareinsights\.com
Segment~Analytics~body~100~cdn\.segment\.(?:com|io)
Mixpanel~Analytics~body~90~cdn\.mxpnl\.com|mixpanel\.com/libs
Sentry~Third-party~body~90~browser\.sentry-cdn\.com|js\.sentry-cdn\.com|sentry\.io/api
reCAPTCHA~Third-party~body~100~google\.com/recaptcha|g-recaptcha
hCaptcha~Third-party~body~100~hcaptcha\.com
Cloudflare Turnstile~Third-party~body~100~challenges\.cloudflare\.com/turnstile
Stripe~Third-party~body~100~js\.stripe\.com
PayPal~Third-party~body~90~paypal(?:objects)?\.com/(?:sdk|tag|js)
Mercado Pago~Third-party~body~90~sdk\.mercadopago\.com|mercadopago\.com/v1
Google Maps~Third-party~body~90~maps\.googleapis\.com|maps\.google\.com/maps
YouTube Embed~Third-party~body~90~youtube(?:-nocookie)?\.com/embed
Intercom~Third-party~body~100~widget\.intercom\.io
Crisp~Third-party~body~100~client\.crisp\.chat
Tawk.to~Third-party~body~100~embed\.tawk\.to
Zendesk~Third-party~body~90~static\.zdassets\.com|zendesk\.com/embeddable
HubSpot~Third-party~body~90~js\.hs-scripts\.com|js\.hsforms\.net|hubspot\.com
Algolia~Third-party~body~60~algolianet\.com|algolia\.net
Firebase~Database~body~80~firebaseio\.com|firebaseapp\.com|firestore\.googleapis\.com
Supabase~Database~body~85~\.supabase\.(?:co|in)
jsDelivr~CDN~script~100~cdn\.jsdelivr\.net
cdnjs~CDN~script~100~cdnjs\.cloudflare\.com
unpkg~CDN~script~100~unpkg\.com
Google Hosted Libraries~CDN~script~100~ajax\.googleapis\.com
Cloudflare~CDN~h:server~100~cloudflare
Cloudflare~CDN~h:cf-ray~100~.
Cloudflare~CDN~h:cf-cache-status~80~.
Cloudflare~CDN~cookie~70~__cf_bm|__cfduid|cf_clearance|__cflb
Akamai~CDN~h:server~100~akamaighost|akamainetworkstorage
Akamai~CDN~h:x-akamai-transformed~100~.
Akamai~CDN~cookie~60~ak_bmsc|bm_sz
Amazon CloudFront~CDN~h:via~100~cloudfront
Amazon CloudFront~CDN~h:x-amz-cf-id~100~.
Amazon CloudFront~CDN~h:x-cache~80~cloudfront
Fastly~CDN~h:x-served-by~60~cache-[a-z0-9]+-[a-z]{3,4}\d*
Fastly~CDN~h:x-fastly-request-id~100~.
Fastly~CDN~h:fastly-debug-digest~100~.
Google Frontend~CDN~h:server~90~^(?:gfe|gws|gse|esf|google frontend)\b
Azure Front Door~CDN~h:x-azure-ref~100~.
Bunny CDN~CDN~h:server~100~bunnycdn
KeyCDN~CDN~h:server~100~keycdn
StackPath~WAF~h:server~100~stackpath
Sucuri~WAF~h:server~100~sucuri
Sucuri~WAF~h:x-sucuri-id~100~.
Imperva~WAF~h:x-iinfo~100~.
Imperva~WAF~h:x-cdn~100~imperva|incapsula
Imperva~WAF~cookie~90~incap_ses|visid_incap|___utmvc
ModSecurity~WAF~h:server~100~mod_security|noyb
F5 BIG-IP~WAF~cookie~80~bigipserver|^ts[0-9a-f]{8}
F5 BIG-IP~WAF~h:x-wa-info~100~.
Barracuda~WAF~cookie~100~barra_counter_session
DDoS-Guard~WAF~h:server~100~ddos-guard
DDoS-Guard~WAF~cookie~80~__ddg\d*_
Wordfence~WAF~body~80~generated by wordfence
Reblaze~WAF~cookie~100~rbzid
AWS WAF~WAF~h:x-amzn-waf-action~100~.
Radware~WAF~h:x-sl-compstate~100~.
Vercel~Hosting~h:server~100~vercel
Vercel~Hosting~h:x-vercel-id~100~.
Netlify~Hosting~h:server~100~netlify
Netlify~Hosting~h:x-nf-request-id~100~.
GitHub Pages~Hosting~h:server~100~github\.com
GitHub Pages~Hosting~h:x-github-request-id~100~.
Heroku~Hosting~h:via~70~vegur
Amazon S3~Hosting~h:server~100~amazons3
Amazon ELB~Hosting~cookie~80~awselb|awsalb
Azure~Hosting~h:server~100~windows-azure|microsoft-azure
Azure~Hosting~h:x-ms-request-id~70~.
Google Cloud Storage~Hosting~h:x-goog-generation~100~.
Fly.io~Hosting~h:server~100~fly\.io
Railway~Hosting~h:server~100~railway
Render~Hosting~h:x-render-origin-server~100~.
HTML5~Markup~body~100~\A\s*<!doctype html>
HTTP/3~Markup~h:alt-svc~100~h3
PWA~Markup~body~60~rel=["']manifest["']
Service Worker~Markup~body~60~serviceworker\.register
Open Graph~Markup~body~60~property=["']og:
Schema.org~Markup~body~60~itemtype=["']https?://schema\.org|application/ld\+json
RSS/Atom~Markup~body~70~application/(?:rss|atom)\+xml
WordPress~CMS~p:/wp-login.php~90~user_login|wp-submit
WordPress~CMS~p:/wp-json/~70~"namespaces"|wp/v2
Joomla~CMS~p:/administrator/~80~joomla
Drupal~CMS~p:/core/CHANGELOG.txt~100~drupal (\d+\.\d+(?:\.\d+)?)
Drupal~CMS~p:/CHANGELOG.txt~100~drupal (\d+\.\d+(?:\.\d+)?)
Magento~E-commerce~p:/magento_version~100~magento/([\d.]+)
Painel phpMyAdmin exposto~Exposure-MED~p:/phpmyadmin/~0~phpmyadmin
Repositório .git exposto~Exposure-HIGH~p:/.git/HEAD~0~^ref:\s*refs/
Arquivo .env acessível~Exposure-HIGH~p:/.env~0~^(?:APP_KEY|DB_PASSWORD|DB_HOST|SECRET_KEY|AWS_SECRET_ACCESS_KEY|MAIL_PASSWORD|DATABASE_URL)=
Apache server-status público~Exposure-MED~p:/server-status~0~apache server status
robots.txt~File~p:/robots.txt~100~user-agent|disallow|sitemap
sitemap.xml~File~p:/sitemap.xml~100~<urlset|<sitemapindex
security.txt~File~p:/.well-known/security.txt~100~contact:
`

var fallbackResolver = &net.Resolver{
	PreferGo: true,
	Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
		d := net.Dialer{Timeout: 4 * time.Second}
		return d.DialContext(ctx, "udp", "1.1.1.1:53")
	},
}

func paint(rgb string, s string) string {
	if !useColor {
		return s
	}
	return "\x1b[38;2;" + rgb + "m" + s + "\x1b[0m"
}

func bold(s string) string {
	if !useColor {
		return s
	}
	return "\x1b[1m" + s + "\x1b[0m"
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}

func capStr(s string, n int) string {
	if len(s) > n {
		return s[:n]
	}
	return s
}

func isTTY(f *os.File) bool {
	fi, err := f.Stat()
	return err == nil && fi.Mode()&os.ModeCharDevice != 0
}

func appendUnique(list []string, v string) []string {
	for _, x := range list {
		if x == v {
			return list
		}
	}
	return append(list, v)
}

func loadRules() {
	seen := map[string]bool{}
	cats := map[string]bool{}
	for _, ln := range strings.Split(sigDB, "\n") {
		ln = strings.TrimSpace(ln)
		if ln == "" {
			continue
		}
		f := strings.SplitN(ln, "~", 5)
		if len(f) != 5 {
			badRules++
			continue
		}
		w, err := strconv.Atoi(f[3])
		if err != nil {
			badRules++
			continue
		}
		re, err := regexp.Compile("(?im)" + f[4])
		if err != nil {
			badRules++
			continue
		}
		r := rule{tech: f[0], cat: f[1], src: f[2], weight: w, re: re}
		if strings.HasPrefix(f[2], "p:") {
			r.path = f[2][2:]
		}
		rules = append(rules, r)
		if !strings.HasPrefix(f[1], "Exposure") && f[1] != "File" {
			seen[f[0]+"|"+f[1]] = true
			cats[f[1]] = true
		}
	}
	techCount = len(seen)
	catCount = len(cats)
}

type spinner struct {
	mu    sync.Mutex
	msg   string
	stopC chan struct{}
	done  chan struct{}
}

func newSpinner(msg string) *spinner {
	s := &spinner{msg: msg, stopC: make(chan struct{}), done: make(chan struct{})}
	go func() {
		frames := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
		i := 0
		t := time.NewTicker(90 * time.Millisecond)
		defer t.Stop()
		defer close(s.done)
		for {
			select {
			case <-s.stopC:
				fmt.Fprint(os.Stderr, "\r\x1b[K")
				return
			case <-t.C:
				s.mu.Lock()
				m := s.msg
				s.mu.Unlock()
				fmt.Fprintf(os.Stderr, "\r\x1b[K%s %s", paint(cRed, frames[i%len(frames)]), paint(cGray, m))
				i++
			}
		}
	}()
	return s
}

func (s *spinner) set(m string) {
	if s == nil {
		return
	}
	s.mu.Lock()
	s.msg = m
	s.mu.Unlock()
}

func (s *spinner) stop() {
	if s == nil {
		return
	}
	close(s.stopC)
	<-s.done
}

func normalizeTarget(raw string) (string, error) {
	t := strings.TrimSpace(raw)
	if t == "" {
		return "", fmt.Errorf("alvo vazio")
	}
	if !strings.Contains(t, "://") {
		t = "https://" + t
	}
	u, err := url.Parse(t)
	if err != nil || u.Host == "" {
		return "", fmt.Errorf("alvo inválido: %s", raw)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", fmt.Errorf("esquema não suportado: %s", u.Scheme)
	}
	return u.String(), nil
}

func resolveIP(host string, timeout time.Duration) string {
	if ip := net.ParseIP(host); ip != nil {
		return ip.String()
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	addrs, err := net.DefaultResolver.LookupHost(ctx, host)
	if err != nil || len(addrs) == 0 {
		ctx2, cancel2 := context.WithTimeout(context.Background(), timeout)
		defer cancel2()
		addrs, err = fallbackResolver.LookupHost(ctx2, host)
		if err != nil || len(addrs) == 0 {
			return ""
		}
	}
	for _, a := range addrs {
		if !strings.Contains(a, ":") {
			return a
		}
	}
	return addrs[0]
}

func dialWithFallback(d *net.Dialer) func(ctx context.Context, network, addr string) (net.Conn, error) {
	return func(ctx context.Context, network, addr string) (net.Conn, error) {
		conn, err := d.DialContext(ctx, network, addr)
		if err == nil {
			return conn, nil
		}
		host, port, serr := net.SplitHostPort(addr)
		if serr != nil || net.ParseIP(host) != nil {
			return nil, err
		}
		ips, lerr := fallbackResolver.LookupHost(ctx, host)
		if lerr != nil || len(ips) == 0 {
			return nil, err
		}
		last := err
		for _, ip := range ips {
			c, derr := d.DialContext(ctx, network, net.JoinHostPort(ip, port))
			if derr == nil {
				return c, nil
			}
			last = derr
		}
		return nil, last
	}
}

func buildTransport(cfg *Config, insecure bool) *http.Transport {
	d := &net.Dialer{Timeout: cfg.Timeout, KeepAlive: 15 * time.Second}
	tr := &http.Transport{
		DialContext:           dialWithFallback(d),
		TLSClientConfig:       &tls.Config{InsecureSkipVerify: insecure, MinVersion: tls.VersionTLS10},
		TLSHandshakeTimeout:   cfg.Timeout,
		ResponseHeaderTimeout: cfg.Timeout,
		ForceAttemptHTTP2:     true,
		MaxIdleConnsPerHost:   4,
	}
	if cfg.Proxy != "" {
		if pu, err := url.Parse(cfg.Proxy); err == nil {
			tr.Proxy = http.ProxyURL(pu)
		}
	} else {
		tr.Proxy = http.ProxyFromEnvironment
	}
	return tr
}

func doGet(cfg *Config, target string, insecure bool, follow bool) (*page, error) {
	chain := []string{target}
	tr := buildTransport(cfg, insecure)
	defer tr.CloseIdleConnections()
	client := &http.Client{
		Transport: tr,
		Timeout:   cfg.Timeout * 2,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if !follow || !cfg.Follow || len(via) >= 6 {
				return http.ErrUseLastResponse
			}
			chain = append(chain, req.URL.String())
			return nil
		},
	}
	req, err := http.NewRequest("GET", target, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", cfg.Agent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8")
	for _, h := range cfg.Headers {
		if i := strings.Index(h, ":"); i > 0 {
			req.Header.Set(strings.TrimSpace(h[:i]), strings.TrimSpace(h[i+1:]))
		}
	}
	if cfg.Cookie != "" {
		req.Header.Set("Cookie", cfg.Cookie)
	}
	start := time.Now()
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
	p := &page{
		URL:     resp.Request.URL.String(),
		Status:  resp.StatusCode,
		Proto:   resp.Proto,
		Header:  resp.Header,
		HL:      map[string]string{},
		Body:    string(body),
		TLS:     resp.TLS,
		Chain:   chain,
		Cookies: resp.Cookies(),
		Dur:     time.Since(start),
	}
	for k, v := range resp.Header {
		p.HL[strings.ToLower(k)] = strings.Join(v, ", ")
	}
	return p, nil
}

func isCertError(err error) bool {
	m := err.Error()
	return strings.Contains(m, "x509") || strings.Contains(m, "certificate")
}

func shortErr(err error) string {
	s := err.Error()
	if i := strings.LastIndex(s, "\": "); i >= 0 {
		s = s[i+3:]
	}
	return truncate(s, 90)
}

func fetchPage(cfg *Config, target string, explicit bool) (*page, string, string, bool, error) {
	insecure := cfg.Insecure
	certNote := ""
	p, err := doGet(cfg, target, insecure, true)
	if err != nil && !insecure && isCertError(err) {
		certNote = shortErr(err)
		insecure = true
		p, err = doGet(cfg, target, true, true)
	}
	if err != nil && !explicit && strings.HasPrefix(target, "https://") {
		alt := "http://" + strings.TrimPrefix(target, "https://")
		p2, err2 := doGet(cfg, alt, cfg.Insecure, true)
		if err2 == nil {
			return p2, alt, "", cfg.Insecure, nil
		}
	}
	return p, target, certNote, insecure, err
}

func extractAssets(p *page) *assets {
	as := &assets{meta: map[string]string{}}
	var refs []string
	for _, m := range reScript.FindAllStringSubmatch(p.Body, 400) {
		as.scripts = append(as.scripts, m[1])
		refs = append(refs, m[1])
	}
	for _, m := range reLink.FindAllStringSubmatch(p.Body, 400) {
		refs = append(refs, m[1])
	}
	as.refs = strings.Join(refs, "\n")
	for _, tag := range reMeta.FindAllString(p.Body, 200) {
		k := reMetaKey.FindStringSubmatch(tag)
		v := reMetaVal.FindStringSubmatch(tag)
		if k != nil && v != nil {
			key := strings.ToLower(strings.TrimSpace(k[1]))
			if _, ok := as.meta[key]; !ok {
				as.meta[key] = strings.TrimSpace(v[1])
			}
		}
	}
	var names []string
	for _, c := range p.Cookies {
		names = append(names, c.Name)
	}
	as.cookies = strings.Join(names, "\n")
	return as
}

func sourceValue(src string, p *page, as *assets) string {
	switch {
	case src == "body":
		return capStr(p.Body, 400000)
	case src == "url":
		return p.URL
	case src == "cookie":
		return as.cookies
	case src == "script":
		return as.refs
	case strings.HasPrefix(src, "h:"):
		return p.HL[src[2:]]
	case strings.HasPrefix(src, "meta:"):
		return as.meta[src[5:]]
	}
	return ""
}

func firstGroup(m []string) string {
	for _, g := range m[1:] {
		if g != "" {
			return strings.Trim(g, ". ")
		}
	}
	return ""
}

func evidence(src string, m []string) string {
	return src + " → " + truncate(reSpace.ReplaceAllString(strings.TrimSpace(m[0]), " "), 60)
}

func addTech(tm map[string]*Tech, name, cat string, w int, ver, ev string) {
	k := name + "|" + cat
	t, ok := tm[k]
	if !ok {
		t = &Tech{Name: name, Cat: cat}
		tm[k] = t
	}
	t.Conf = minInt(100, t.Conf+w)
	if ver != "" && len(ver) > len(t.Version) {
		t.Version = ver
	}
	if ev != "" && len(t.Evidence) < 4 {
		t.Evidence = append(t.Evidence, ev)
	}
}

func analyze(p *page, as *assets, tm map[string]*Tech) {
	for i := range rules {
		r := &rules[i]
		if r.path != "" {
			continue
		}
		v := sourceValue(r.src, p, as)
		if v == "" {
			continue
		}
		m := r.re.FindStringSubmatch(v)
		if m == nil {
			continue
		}
		addTech(tm, r.tech, r.cat, r.weight, firstGroup(m), evidence(r.src, m))
	}
}

func applyImplies(tm map[string]*Tech) {
	for pass := 0; pass < 2; pass++ {
		parents := make([]*Tech, 0, len(tm))
		for _, t := range tm {
			parents = append(parents, t)
		}
		for _, t := range parents {
			if t.Conf < 40 {
				continue
			}
			for _, im := range implies[t.Name] {
				k := im.name + "|" + im.cat
				if _, ok := tm[k]; ok {
					continue
				}
				tm[k] = &Tech{
					Name:     im.name,
					Cat:      im.cat,
					Conf:     im.conf * t.Conf / 100,
					Inferred: true,
					Evidence: []string{"implícito por " + t.Name},
				}
			}
		}
	}
}

func catRank(cat string) int {
	for i, s := range stackOrder {
		if s.cat == cat {
			return i
		}
	}
	return 99
}

func sortedTechs(tm map[string]*Tech) []*Tech {
	out := make([]*Tech, 0, len(tm))
	for _, t := range tm {
		if t.Conf >= 30 {
			out = append(out, t)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		ri, rj := catRank(out[i].Cat), catRank(out[j].Cat)
		if ri != rj {
			return ri < rj
		}
		if out[i].Conf != out[j].Conf {
			return out[i].Conf > out[j].Conf
		}
		return out[i].Name < out[j].Name
	})
	return out
}

func wafList(techs []*Tech) []string {
	var out []string
	for _, t := range techs {
		if t.Cat == "WAF" || (t.Cat == "CDN" && wafAlso[t.Name] && t.Conf >= 60) {
			out = appendUnique(out, t.Name)
		}
	}
	return out
}

func hasTech(techs []*Tech, name string) bool {
	for _, t := range techs {
		if t.Name == name {
			return true
		}
	}
	return false
}

func inferOS(p *page, techs []*Tech) string {
	blob := strings.ToLower(p.HL["server"] + " " + p.HL["x-powered-by"] + " " + p.HL["via"])
	known := []struct{ k, v string }{
		{"ubuntu", "Linux (Ubuntu)"},
		{"debian", "Linux (Debian)"},
		{"centos", "Linux (CentOS)"},
		{"red hat", "Linux (RHEL)"},
		{"rhel", "Linux (RHEL)"},
		{"fedora", "Linux (Fedora)"},
		{"alpine", "Linux (Alpine)"},
		{"freebsd", "FreeBSD"},
		{"openbsd", "OpenBSD"},
		{"win64", "Windows"},
		{"win32", "Windows"},
		{"windows", "Windows"},
		{"unix", "Unix"},
	}
	for _, e := range known {
		if strings.Contains(blob, e.k) {
			return e.v
		}
	}
	if hasTech(techs, "Microsoft IIS") || hasTech(techs, "ASP.NET") || hasTech(techs, "Kestrel") {
		return "Windows (inferido)"
	}
	for _, n := range []string{"Nginx", "Apache", "LiteSpeed", "OpenResty", "lighttpd", "Gunicorn", "Caddy", "Puma", "Phusion Passenger"} {
		if hasTech(techs, n) {
			return "Linux/Unix (genérico, inferido)"
		}
	}
	return "Não identificado"
}

func verParts(v string) []int {
	var out []int
	for _, s := range strings.Split(v, ".") {
		n := 0
		for _, ch := range s {
			if ch < '0' || ch > '9' {
				break
			}
			n = n*10 + int(ch-'0')
		}
		out = append(out, n)
	}
	return out
}

func verLess(a, b string) bool {
	pa, pb := verParts(a), verParts(b)
	for i := 0; i < len(pa) || i < len(pb); i++ {
		var x, y int
		if i < len(pa) {
			x = pa[i]
		}
		if i < len(pb) {
			y = pb[i]
		}
		if x != y {
			return x < y
		}
	}
	return false
}

func verMajor(v string) int {
	return verParts(v)[0]
}

func libIssue(name, ver string) (string, string) {
	label := name
	if ver != "" {
		label += " " + ver
	}
	switch name {
	case "AngularJS":
		return "MÉDIO", "AngularJS sem suporte desde jan/2022: " + label
	}
	if ver == "" {
		return "", ""
	}
	switch name {
	case "jQuery":
		if verLess(ver, "3.5.0") {
			return "MÉDIO", "jQuery vulnerável a XSS (CVE-2020-11022/11023): " + label
		}
	case "jQuery UI":
		if verLess(ver, "1.13.2") {
			return "BAIXO", "jQuery UI desatualizado (CVE-2022-31160): " + label
		}
	case "Bootstrap":
		m := verMajor(ver)
		if m < 3 || (m == 3 && verLess(ver, "3.4.1")) || (m == 4 && verLess(ver, "4.3.1")) {
			return "MÉDIO", "Bootstrap com XSS conhecido (CVE-2019-8331/CVE-2018-14040): " + label
		}
	case "Lodash":
		if verLess(ver, "4.17.21") {
			return "MÉDIO", "Lodash vulnerável a prototype pollution (CVE-2021-23337): " + label
		}
	case "Moment.js":
		if verLess(ver, "2.29.4") {
			return "BAIXO", "Moment.js vulnerável a ReDoS (CVE-2022-31129): " + label
		}
	case "Underscore.js":
		if verLess(ver, "1.12.1") {
			return "BAIXO", "Underscore.js vulnerável (CVE-2021-23358): " + label
		}
	case "Handlebars":
		if verLess(ver, "4.7.7") {
			return "MÉDIO", "Handlebars vulnerável (CVE-2021-23369): " + label
		}
	case "Axios":
		if verLess(ver, "0.21.2") {
			return "BAIXO", "Axios vulnerável a ReDoS (CVE-2021-3749): " + label
		}
	case "Vue.js":
		if verMajor(ver) == 2 {
			return "INFO", "Vue 2 chegou ao fim de vida (dez/2023): " + label
		}
	case "React":
		if verMajor(ver) < 17 {
			return "INFO", "Biblioteca JS desatualizada: " + label
		}
	case "PHP":
		if verLess(ver, "8.2") {
			return "MÉDIO", "PHP sem suporte de segurança oficial: " + label
		}
	case "Apache":
		if verLess(ver, "2.4.0") {
			return "MÉDIO", "Apache 2.2 ou anterior sem suporte: " + label
		}
	case "Drupal":
		if verMajor(ver) <= 9 {
			return "MÉDIO", "Drupal sem suporte (fim de vida): " + label
		}
	case "Joomla":
		if verMajor(ver) <= 3 {
			return "MÉDIO", "Joomla sem suporte (fim de vida): " + label
		}
	}
	return "", ""
}

func hstsAge(v string) int {
	m := reHSTSAge.FindStringSubmatch(v)
	if m == nil {
		return -1
	}
	n, err := strconv.Atoi(m[1])
	if err != nil {
		return -1
	}
	return n
}

func tlsName(v uint16) string {
	switch v {
	case tls.VersionTLS10:
		return "TLS 1.0"
	case tls.VersionTLS11:
		return "TLS 1.1"
	case tls.VersionTLS12:
		return "TLS 1.2"
	case tls.VersionTLS13:
		return "TLS 1.3"
	}
	return "TLS desconhecido"
}

func sevRank(s string) int {
	switch s {
	case "ALTO":
		return 0
	case "MÉDIO":
		return 1
	case "BAIXO":
		return 2
	}
	return 3
}

func expSev(cat string) string {
	switch strings.TrimPrefix(cat, "Exposure-") {
	case "HIGH":
		return "ALTO"
	case "MED":
		return "MÉDIO"
	}
	return "BAIXO"
}

func softMatch(base, pg *page) bool {
	if base == nil || base.Status != 200 {
		return false
	}
	a, b := len(base.Body), len(pg.Body)
	d := a - b
	if d < 0 {
		d = -d
	}
	return d*100 <= a*5
}

func deepProbe(cfg *Config, p *page, res *Result, tm map[string]*Tech, insecure bool) {
	u, err := url.Parse(p.URL)
	if err != nil {
		return
	}
	base := u.Scheme + "://" + u.Host
	stamp := strconv.FormatInt(time.Now().UnixNano(), 36)
	baseline, _ := doGet(cfg, base+"/moonscan-"+stamp+"-inexistente", insecure, false)
	if baseline != nil {
		analyze(baseline, extractAssets(baseline), tm)
	}
	var paths []string
	seen := map[string]bool{}
	for i := range rules {
		pa := rules[i].path
		if pa != "" && !seen[pa] {
			seen[pa] = true
			paths = append(paths, pa)
		}
	}
	got := map[string]*page{}
	var mu sync.Mutex
	var wg sync.WaitGroup
	sem := make(chan struct{}, cfg.Threads)
	for _, pa := range paths {
		wg.Add(1)
		go func(pa string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			pg, gerr := doGet(cfg, base+pa, insecure, false)
			if gerr != nil {
				return
			}
			mu.Lock()
			got[pa] = pg
			mu.Unlock()
		}(pa)
	}
	wg.Wait()
	for i := range rules {
		r := &rules[i]
		if r.path == "" {
			continue
		}
		pg := got[r.path]
		if pg == nil {
			continue
		}
		isExp := strings.HasPrefix(r.cat, "Exposure-")
		okStatus := pg.Status == 200 || (pg.Status == 401 && !isExp && r.cat != "File")
		if !okStatus || softMatch(baseline, pg) {
			continue
		}
		m := r.re.FindStringSubmatch(capStr(pg.Body, 200000))
		if m == nil {
			continue
		}
		switch {
		case isExp:
			res.Findings = append(res.Findings, Finding{Sev: expSev(r.cat), Title: r.tech, Detail: "GET " + r.path})
		case r.cat == "File":
			res.Files = appendUnique(res.Files, r.path)
		default:
			addTech(tm, r.tech, r.cat, r.weight, firstGroup(m), "GET "+r.path+" → "+truncate(reSpace.ReplaceAllString(strings.TrimSpace(m[0]), " "), 40))
		}
	}
}

func geoLookup(ip string) string {
	pip := net.ParseIP(ip)
	if pip == nil || pip.IsPrivate() || pip.IsLoopback() {
		return ""
	}
	c := &http.Client{Timeout: 5 * time.Second}
	resp, err := c.Get("http://ip-api.com/json/" + ip + "?fields=status,country,regionName,city,isp&lang=pt-BR")
	if err != nil {
		return ""
	}
	defer resp.Body.Close()
	var g struct {
		Status  string `json:"status"`
		Country string `json:"country"`
		Region  string `json:"regionName"`
		City    string `json:"city"`
		ISP     string `json:"isp"`
	}
	if json.NewDecoder(io.LimitReader(resp.Body, 65536)).Decode(&g) != nil || g.Status != "success" {
		return ""
	}
	var parts []string
	for _, v := range []string{g.City, g.Region, g.Country} {
		if v != "" {
			parts = append(parts, v)
		}
	}
	out := strings.Join(parts, ", ")
	if g.ISP != "" {
		out += " · " + g.ISP
	}
	return out
}

func pageTitle(body string) string {
	m := reTitle.FindStringSubmatch(body)
	if m == nil {
		return ""
	}
	t := strings.TrimSpace(reSpace.ReplaceAllString(html.UnescapeString(m[1]), " "))
	return truncate(t, 70)
}

func audit(p *page, as *assets, res *Result, certNote string) {
	add := func(sev, title, detail string) {
		res.Findings = append(res.Findings, Finding{Sev: sev, Title: title, Detail: detail})
	}
	isHTTPS := strings.HasPrefix(p.URL, "https://")
	isHTML := strings.Contains(p.HL["content-type"], "html")
	csp := p.HL["content-security-policy"]
	if !isHTTPS {
		add("MÉDIO", "Conexão sem criptografia (HTTP)", "o endereço final é servido via HTTP")
		if rePass.MatchString(p.Body) {
			add("ALTO", "Formulário de senha servido sem HTTPS", "")
		}
	}
	if isHTML {
		if p.HL["x-frame-options"] == "" && !strings.Contains(strings.ToLower(csp), "frame-ancestors") {
			add("MÉDIO", "Header: X-Frame-Options ausente (Clickjacking)", "")
		}
		if csp == "" {
			add("MÉDIO", "Header: Content-Security-Policy ausente", "")
		} else if reWeakCSP.MatchString(csp) {
			add("BAIXO", "Header: Content-Security-Policy não estrito", truncate(csp, 120))
		}
		if !strings.EqualFold(p.HL["x-content-type-options"], "nosniff") {
			add("BAIXO", "Header: X-Content-Type-Options ausente", "")
		}
		if p.HL["referrer-policy"] == "" {
			add("INFO", "Header: Referrer-Policy ausente", "")
		}
		if p.HL["permissions-policy"] == "" {
			add("INFO", "Header: Permissions-Policy ausente", "")
		}
	}
	if isHTTPS {
		hsts := p.HL["strict-transport-security"]
		if hsts == "" {
			add("MÉDIO", "Header: Strict-Transport-Security ausente (HSTS)", "")
		} else if age := hstsAge(hsts); age >= 0 && age < 15552000 {
			add("BAIXO", "HSTS com max-age curto ("+strconv.Itoa(age)+"s)", "")
		}
	}
	for _, h := range []string{"server", "x-powered-by", "x-aspnet-version"} {
		v := p.HL[h]
		if v != "" && reVerShow.MatchString(v) {
			add("BAIXO", "Divulgação de versão ("+h+"): "+truncate(v, 50), "")
		}
	}
	var noSecure, noHTTP, noSame []string
	for _, c := range p.Cookies {
		if isHTTPS && !c.Secure {
			noSecure = append(noSecure, c.Name)
		}
		if !c.HttpOnly {
			noHTTP = append(noHTTP, c.Name)
		}
		if c.SameSite == 0 {
			noSame = append(noSame, c.Name)
		}
	}
	if len(noSecure) > 0 {
		add("BAIXO", "Cookies sem flag Secure: "+strings.Join(noSecure[:minInt(4, len(noSecure))], ", "), "")
	}
	if len(noHTTP) > 0 {
		add("BAIXO", "Cookies sem flag HttpOnly: "+strings.Join(noHTTP[:minInt(4, len(noHTTP))], ", "), "")
	}
	if len(noSame) > 0 {
		add("INFO", "Cookies sem SameSite: "+strings.Join(noSame[:minInt(4, len(noSame))], ", "), "")
	}
	if p.HL["access-control-allow-origin"] == "*" {
		if strings.EqualFold(p.HL["access-control-allow-credentials"], "true") {
			add("MÉDIO", "CORS: wildcard com credenciais habilitadas", "")
		} else {
			add("INFO", "CORS: Access-Control-Allow-Origin: *", "")
		}
	}
	if strings.Contains(strings.ToLower(capStr(p.Body, 4000)), "<title>index of /") {
		add("MÉDIO", "Listagem de diretório habilitada", "")
	}
	if isHTTPS {
		n := 0
		for _, s := range as.scripts {
			if strings.HasPrefix(strings.ToLower(s), "http://") {
				n++
			}
		}
		if n > 0 {
			add("BAIXO", fmt.Sprintf("Mixed content: %d script(s) carregado(s) via HTTP", n), "")
		}
	}
	if p.TLS != nil {
		if p.TLS.Version == tls.VersionTLS10 || p.TLS.Version == tls.VersionTLS11 {
			add("ALTO", "TLS obsoleto negociado: "+tlsName(p.TLS.Version), "")
		}
		if len(p.TLS.PeerCertificates) > 0 {
			days := int(time.Until(p.TLS.PeerCertificates[0].NotAfter).Hours() / 24)
			if days < 0 {
				add("ALTO", "Certificado TLS expirado", "")
			} else if days <= 14 {
				add("MÉDIO", fmt.Sprintf("Certificado TLS expira em %d dia(s)", days), "")
			}
		}
	}
	if certNote != "" {
		add("ALTO", "Certificado TLS não confiável: "+certNote, "")
	}
	for _, t := range res.Techs {
		if t.Inferred {
			continue
		}
		if sev, msg := libIssue(t.Name, t.Version); msg != "" {
			add(sev, msg, "")
		}
	}
	sort.SliceStable(res.Findings, func(i, j int) bool {
		return sevRank(res.Findings[i].Sev) < sevRank(res.Findings[j].Sev)
	})
}

func scan(cfg *Config, raw string, sp *spinner) *Result {
	res := &Result{
		Target:   raw,
		Date:     time.Now().Format(time.RFC3339),
		Deep:     cfg.Deep,
		Techs:    []*Tech{},
		Findings: []Finding{},
	}
	explicit := strings.Contains(raw, "://")
	target, err := normalizeTarget(raw)
	if err != nil {
		res.Error = err.Error()
		return res
	}
	res.Target = target
	u, _ := url.Parse(target)
	sp.set("Resolvendo DNS")
	res.IP = resolveIP(u.Hostname(), cfg.Timeout)
	var geoCh chan string
	if !cfg.NoGeo && res.IP != "" {
		geoCh = make(chan string, 1)
		go func(ip string) { geoCh <- geoLookup(ip) }(res.IP)
	}
	sp.set("Coletando resposta HTTP")
	p, used, certNote, insecure, err := fetchPage(cfg, target, explicit)
	if err != nil {
		res.Target = used
		res.Error = shortErr(err)
		return res
	}
	res.Target = used
	res.FinalURL = p.URL
	res.Status = p.Status
	res.Proto = p.Proto
	res.TimeMs = p.Dur.Milliseconds()
	if len(p.Chain) > 1 {
		res.Redirects = p.Chain
	}
	res.Server = p.HL["server"]
	res.PoweredBy = p.HL["x-powered-by"]
	res.Title = pageTitle(p.Body)
	if p.TLS != nil {
		res.TLS = tlsName(p.TLS.Version) + " · " + tls.CipherSuiteName(p.TLS.CipherSuite)
		if len(p.TLS.PeerCertificates) > 0 {
			cert := p.TLS.PeerCertificates[0]
			issuer := cert.Issuer.CommonName
			if issuer == "" && len(cert.Issuer.Organization) > 0 {
				issuer = cert.Issuer.Organization[0]
			}
			days := int(time.Until(cert.NotAfter).Hours() / 24)
			if days < 0 {
				res.Cert = issuer + " · expirado"
			} else {
				res.Cert = fmt.Sprintf("%s · expira em %d dia(s)", issuer, days)
			}
		}
	}
	for _, c := range p.Cookies {
		var fl []string
		if c.Secure {
			fl = append(fl, "Secure")
		}
		if c.HttpOnly {
			fl = append(fl, "HttpOnly")
		}
		if c.SameSite != 0 {
			fl = append(fl, "SameSite")
		}
		entry := c.Name
		if len(fl) > 0 {
			entry += " (" + strings.Join(fl, ",") + ")"
		}
		res.Cookies = append(res.Cookies, entry)
	}
	for _, e := range reEmail.FindAllString(capStr(p.Body, 400000), 80) {
		low := strings.ToLower(e)
		ext := low[strings.LastIndex(low, ".")+1:]
		if badMailExt[ext] || len(res.Emails) >= 5 {
			continue
		}
		res.Emails = appendUnique(res.Emails, low)
	}
	for k := range p.HL {
		if !commonHeaders[k] {
			res.ExtraHeaders = append(res.ExtraHeaders, k)
		}
	}
	sort.Strings(res.ExtraHeaders)
	if len(res.ExtraHeaders) > 14 {
		res.ExtraHeaders = res.ExtraHeaders[:14]
	}
	sp.set("Analisando assinaturas")
	as := extractAssets(p)
	tm := map[string]*Tech{}
	analyze(p, as, tm)
	if cfg.Deep {
		sp.set("Sondagem profunda de caminhos")
		deepProbe(cfg, p, res, tm, insecure)
	}
	applyImplies(tm)
	res.Techs = sortedTechs(tm)
	res.WAF = wafList(res.Techs)
	res.OS = inferOS(p, res.Techs)
	sp.set("Auditando headers e configuração")
	audit(p, as, res, certNote)
	if geoCh != nil {
		sp.set("Consultando geolocalização")
		res.Geo = <-geoCh
	}
	return res
}

func row(mark, mrgb, label, value, vrgb string) {
	fmt.Printf("%s %s: %s\n", paint(mrgb, mark), paint(cCyan, fmt.Sprintf("%-16s", label)), paint(vrgb, value))
}

func fmtTech(t *Tech) string {
	s := t.Name
	if t.Version != "" {
		if t.Version[0] >= '0' && t.Version[0] <= '9' {
			s += " v" + t.Version
		} else {
			s += " " + t.Version
		}
	}
	if t.Inferred {
		return s + " [inferido " + strconv.Itoa(t.Conf) + "%]"
	}
	return s + " [" + strconv.Itoa(t.Conf) + "%]"
}

func printResult(cfg *Config, res *Result) {
	mode := "Scanning Standard/Passive"
	if res.Deep {
		mode = "Scanning Deep/Aggressive"
	}
	ip := ""
	if res.IP != "" {
		ip = " (" + res.IP + ")"
	}
	fmt.Println(paint(cCyan, "[>] Target: "+res.Target+ip) + " " + paint(cGreen, "["+mode+"]"))
	if res.Error != "" {
		fmt.Println(paint(cRed, "[✗] Falha: "+res.Error))
		fmt.Println()
		return
	}
	fmt.Println(bold(paint(cCyan, "[📡 INFO]")))
	server := res.Server
	if server == "" {
		server = "oculto"
	}
	row("[✓]", cGreen, "Server", server, cWhite)
	row("[✓]", cGreen, "OS", res.OS, cWhite)
	if len(res.WAF) > 0 {
		row("[!]", cRed, "Firewall", "WAF Detected ("+strings.Join(res.WAF, ", ")+")", cRed)
	} else {
		row("[✓]", cGreen, "Firewall", "Nenhum WAF identificado", cWhite)
	}
	switch {
	case res.Geo != "":
		row("[✓]", cGreen, "IP Geolocation", res.Geo, cWhite)
	case cfg.NoGeo:
		row("[i]", cGray, "IP Geolocation", "desativada (--no-geo)", cGray)
	default:
		row("[i]", cGray, "IP Geolocation", "indisponível", cGray)
	}
	if res.Title != "" {
		row("[✓]", cGreen, "Title", res.Title, cWhite)
	}
	row("[✓]", cGreen, "HTTP", fmt.Sprintf("%d · %s · %dms", res.Status, res.Proto, res.TimeMs), cWhite)
	if res.TLS != "" {
		row("[✓]", cGreen, "TLS", res.TLS, cWhite)
		if res.Cert != "" {
			row("[✓]", cGreen, "Certificate", res.Cert, cWhite)
		}
	}
	if len(res.Files) > 0 {
		row("[✓]", cGreen, "Files", strings.Join(res.Files, ", "), cWhite)
	}
	if cfg.Verbose {
		if len(res.Redirects) > 1 {
			row("[>]", cCyan, "Redirects", strings.Join(res.Redirects, " → "), cWhite)
		}
		if res.PoweredBy != "" {
			row("[>]", cCyan, "Powered-By", res.PoweredBy, cWhite)
		}
		if len(res.Cookies) > 0 {
			row("[>]", cCyan, "Cookies", strings.Join(res.Cookies, ", "), cWhite)
		}
		if len(res.Emails) > 0 {
			row("[>]", cCyan, "Emails", strings.Join(res.Emails, ", "), cWhite)
		}
		if len(res.ExtraHeaders) > 0 {
			row("[>]", cCyan, "Extra Headers", strings.Join(res.ExtraHeaders, ", "), cWhite)
		}
	}
	fmt.Println(bold(paint(cCyan, "[🧬 TECH STACK]")))
	for _, so := range stackOrder {
		var items []string
		var evs []string
		for _, t := range res.Techs {
			if t.Cat != so.cat {
				continue
			}
			items = append(items, fmtTech(t))
			if cfg.Verbose {
				for _, e := range t.Evidence {
					evs = append(evs, t.Name+" ← "+e)
				}
			}
		}
		if len(items) == 0 {
			if so.core {
				row("[>]", cGray, so.label, "nenhum detectado", cGray)
			}
			continue
		}
		row("[>]", cCyan, so.label, strings.Join(items, ", "), cWhite)
		for _, e := range evs[:minInt(3, len(evs))] {
			fmt.Println("    " + paint(cGray, "└ "+truncate(e, 90)))
		}
	}
	fmt.Println(bold(paint(cCyan, "[🛡️ VULNERABILITIES]")))
	if len(res.Findings) == 0 {
		fmt.Println(paint(cGreen, "[✓] Nenhum achado nas verificações realizadas"))
	}
	counts := map[string]int{}
	for _, f := range res.Findings {
		counts[f.Sev]++
		mark, rgb := "[!]", cRed
		switch f.Sev {
		case "MÉDIO":
			rgb = cYellow
		case "BAIXO":
			mark, rgb = "[-]", cCyan
		case "INFO":
			mark, rgb = "[i]", cGreen
		}
		txt := f.Title
		if cfg.Verbose && f.Detail != "" {
			txt += " — " + f.Detail
		}
		fmt.Println(paint(rgb, mark+" "+txt))
	}
	if len(res.Findings) > 0 {
		fmt.Println(paint(cGray, fmt.Sprintf("[Σ] %d alto · %d médio · %d baixo · %d info", counts["ALTO"], counts["MÉDIO"], counts["BAIXO"], counts["INFO"])))
	}
	fmt.Println()
}

func hostLabel(target string) string {
	u, err := url.Parse(target)
	if err != nil || u.Host == "" {
		return "alvo"
	}
	h := strings.TrimPrefix(strings.ToLower(u.Host), "www.")
	h = strings.NewReplacer(".", "_", ":", "_").Replace(h)
	return h
}

func saveReports(cfg *Config, results []*Result) {
	var payload interface{}
	if len(results) == 1 {
		payload = results[0]
	} else {
		payload = results
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return
	}
	if cfg.JSON {
		fmt.Println(string(data))
	}
	if cfg.Output == "" && (cfg.NoReport || cfg.JSON) {
		return
	}
	name := cfg.Output
	if name == "" {
		if len(results) == 1 {
			name = "moonscan_report_" + hostLabel(results[0].Target) + ".json"
		} else {
			name = "moonscan_report_lote_" + strconv.FormatInt(time.Now().Unix(), 10) + ".json"
		}
	}
	if werr := os.WriteFile(name, data, 0o644); werr != nil {
		fmt.Fprintln(os.Stderr, paint(cRed, "[✗] Falha ao salvar relatório: "+werr.Error()))
		return
	}
	if !cfg.JSON {
		fmt.Println(paint(cGreen, "[✨]") + " Relatório salvo em: " + paint(cWhite, name))
	}
}

func runTargets(cfg *Config, targets []string) int {
	results := make([]*Result, len(targets))
	showSpin := len(targets) == 1 && !cfg.JSON && isTTY(os.Stderr)
	var wg sync.WaitGroup
	var mu sync.Mutex
	sem := make(chan struct{}, cfg.Threads)
	for i, t := range targets {
		wg.Add(1)
		go func(i int, t string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			var sp *spinner
			if showSpin {
				sp = newSpinner("Iniciando varredura")
			}
			res := scan(cfg, t, sp)
			sp.stop()
			mu.Lock()
			results[i] = res
			if !cfg.JSON {
				printResult(cfg, res)
			}
			mu.Unlock()
		}(i, t)
	}
	wg.Wait()
	failed := 0
	for _, r := range results {
		if r.Error != "" {
			failed++
		}
	}
	if failed < len(results) {
		saveReports(cfg, results)
	}
	return failed
}

func printBanner() {
	fmt.Println()
	for _, l := range bannerLines {
		fmt.Println(paint(cRed, l))
	}
	fmt.Println()
	mark := paint(cRed, "◆")
	fmt.Printf("  %s %s %s\n", mark, bold(paint(cWhite, appName+" "+appVersion)), paint(cGray, "── Web Fingerprint & Recon Engine · Termux Edition"))
	fmt.Printf("  %s %s\n", mark, paint(cGray, "Inspirado no WhatWeb · motor nativo em Go · zero dependências"))
	fmt.Printf("  %s %s\n", mark, paint(cGray, fmt.Sprintf("%d assinaturas · %d tecnologias · %d categorias · modos standard e deep", len(rules), techCount, catCount)))
	fmt.Printf("  %s %s\n", mark, paint(cGray, "Console interativo: moonscan   ·   Ajuda: moonscan -h"))
	fmt.Printf("  %s %s\n\n", paint(cYellow, "[!]"), paint(cYellow, "Use somente em alvos que você possui ou tem autorização para testar."))
}

func hl(flag, desc string) {
	fmt.Printf("  %s %s\n", paint(cCyan, fmt.Sprintf("%-22s", flag)), paint(cWhite, desc))
}

func sec(title string) {
	fmt.Println(bold(paint(cRed, title)))
}

func printHelp() {
	sec("USO")
	hl("moonscan <alvo>", "varredura padrão de um alvo")
	hl("moonscan [opções] <alvos>", "um ou mais alvos (URL, domínio ou IP)")
	hl("moonscan", "abre o console interativo")
	hl("cat alvos | moonscan -a", "lê alvos pelo stdin")
	fmt.Println()
	sec("MODOS")
	hl("padrão", "leve: 1 requisição + análise de assinaturas e headers")
	hl("-a, --deep", "agressivo: baseline 404, sondagem de caminhos e exposições")
	fmt.Println()
	sec("OPÇÕES")
	hl("-v, --verbose", "evidências, cookies, e-mails e headers extras")
	hl("-l, --list ARQ", "arquivo com alvos (um por linha)")
	hl("-t, --threads N", "alvos em paralelo (padrão 5)")
	hl("-T, --timeout S", "timeout em segundos (padrão 12)")
	hl("-A, --agent UA", "User-Agent personalizado")
	hl("-H, --header 'K: V'", "header extra (repetível)")
	hl("-c, --cookie STR", "cookie enviado nas requisições")
	hl("-x, --proxy URL", "http://, https:// ou socks5://")
	hl("-k, --insecure", "ignora erros de certificado TLS")
	hl("    --no-follow", "não segue redirecionamentos")
	hl("    --no-geo", "não consulta geolocalização (ip-api.com)")
	hl("-o, --output ARQ", "arquivo JSON do relatório")
	hl("    --json", "imprime só JSON no stdout")
	hl("    --no-report", "não salva relatório")
	hl("    --no-color", "sem cores")
	hl("    --color", "força cores mesmo em pipe")
	hl("    --no-banner", "oculta o banner")
	hl("    --techs", "lista categorias e tecnologias")
	hl("-i, --console", "abre o console interativo")
	hl("-V, --version", "mostra a versão")
	hl("-h, --help", "esta ajuda")
	fmt.Println()
	sec("EXEMPLOS")
	hl("moonscan -v exemplo.com", "varredura com evidências")
	hl("moonscan -a -t 8 -l alvos.txt", "deep em lote com 8 threads")
	hl("moonscan --json -a site.com", "saída JSON para pipeline")
	hl("moonscan -x socks5://127.0.0.1:9050 -k site.com", "via proxy, sem validar TLS")
	fmt.Println()
}

func printConsoleHelp() {
	sec("COMANDOS")
	hl("scan <alvo>", "varredura padrão")
	hl("deep <alvo>", "varredura profunda (agressiva)")
	hl("batch <arquivo>", "varre vários alvos de um arquivo")
	hl("set <opção> <valor>", "altera uma opção")
	hl("show", "mostra a configuração atual")
	hl("techs", "lista categorias e tecnologias")
	hl("banner", "mostra o banner")
	hl("clear", "limpa a tela")
	hl("help", "esta ajuda")
	hl("exit", "sai do console")
	fmt.Println()
	sec("OPÇÕES DO set")
	hl("threads <1-50>", "alvos em paralelo")
	hl("timeout <seg>", "timeout das requisições")
	hl("agent <texto>", "User-Agent")
	hl("proxy <url|off>", "proxy de saída")
	hl("cookie <texto>", "cookie das requisições")
	hl("header <K: V>", "adiciona header extra")
	hl("verbose on|off", "modo detalhado")
	hl("insecure on|off", "ignorar erros TLS")
	hl("follow on|off", "seguir redirecionamentos")
	hl("geo on|off", "geolocalização de IP")
	hl("report on|off", "salvar relatório JSON")
	fmt.Println()
	fmt.Println(paint(cGray, "  Dica: digitar apenas um domínio já executa o scan."))
	fmt.Println()
}

func printTechs() {
	groups := map[string][]string{}
	seen := map[string]bool{}
	for _, r := range rules {
		if strings.HasPrefix(r.cat, "Exposure") || r.cat == "File" {
			continue
		}
		k := r.tech + "|" + r.cat
		if seen[k] {
			continue
		}
		seen[k] = true
		groups[r.cat] = append(groups[r.cat], r.tech)
	}
	var cats []string
	for c := range groups {
		cats = append(cats, c)
	}
	sort.Slice(cats, func(i, j int) bool {
		ri, rj := catRank(cats[i]), catRank(cats[j])
		if ri != rj {
			return ri < rj
		}
		return cats[i] < cats[j]
	})
	for _, c := range cats {
		sort.Strings(groups[c])
		fmt.Printf("%s %s\n", paint(cRed, fmt.Sprintf("[%d]", len(groups[c]))), bold(paint(cCyan, c)))
		fmt.Println("    " + paint(cGray, strings.Join(groups[c], ", ")))
	}
	fmt.Println()
	fmt.Println(paint(cGreen, fmt.Sprintf("[✓] %d assinaturas · %d tecnologias · %d categorias", len(rules), techCount, catCount)))
}

func onOff(b bool) string {
	if b {
		return "on"
	}
	return "off"
}

func parseBool(v string) bool {
	switch strings.ToLower(v) {
	case "on", "true", "1", "sim", "yes", "s", "y":
		return true
	}
	return false
}

func showConfig(cfg *Config) {
	r := func(k, v string) {
		fmt.Printf("  %s %s\n", paint(cCyan, fmt.Sprintf("%-10s", k)), paint(cWhite, v))
	}
	proxy := cfg.Proxy
	if proxy == "" {
		proxy = "nenhum"
	}
	r("threads", strconv.Itoa(cfg.Threads))
	r("timeout", fmt.Sprintf("%ds", int(cfg.Timeout/time.Second)))
	r("verbose", onOff(cfg.Verbose))
	r("insecure", onOff(cfg.Insecure))
	r("follow", onOff(cfg.Follow))
	r("geo", onOff(!cfg.NoGeo))
	r("report", onOff(!cfg.NoReport))
	r("proxy", proxy)
	r("agent", truncate(cfg.Agent, 60))
	r("headers", strconv.Itoa(len(cfg.Headers)))
	fmt.Println()
}

func setOption(cfg *Config, key, val string) string {
	key = strings.ToLower(key)
	switch key {
	case "threads":
		n, err := strconv.Atoi(val)
		if err != nil || n < 1 || n > 50 {
			return "threads: use um valor de 1 a 50"
		}
		cfg.Threads = n
	case "timeout":
		n, err := strconv.Atoi(val)
		if err != nil || n < 1 || n > 120 {
			return "timeout: use um valor de 1 a 120"
		}
		cfg.Timeout = time.Duration(n) * time.Second
	case "agent":
		cfg.Agent = val
	case "proxy":
		if strings.EqualFold(val, "off") || strings.EqualFold(val, "none") {
			cfg.Proxy = ""
		} else {
			cfg.Proxy = val
		}
	case "cookie":
		cfg.Cookie = val
	case "header":
		cfg.Headers = append(cfg.Headers, val)
	case "verbose":
		cfg.Verbose = parseBool(val)
	case "insecure":
		cfg.Insecure = parseBool(val)
	case "follow":
		cfg.Follow = parseBool(val)
	case "geo":
		cfg.NoGeo = !parseBool(val)
	case "report":
		cfg.NoReport = !parseBool(val)
	default:
		return "opção desconhecida: " + key
	}
	return ""
}

func readTargets(r io.Reader) []string {
	var out []string
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for sc.Scan() {
		t := strings.TrimSpace(sc.Text())
		if t != "" {
			out = append(out, t)
		}
	}
	return out
}

func readTargetFile(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return readTargets(f), nil
}

func prompt() string {
	return paint(cRed, "moonscan") + paint(cGray, "@") + paint(cCyan, "termux") + paint(cGray, ":~") + paint(cWhite, "$ ")
}

func console(cfg *Config) {
	sc := bufio.NewScanner(os.Stdin)
	for {
		fmt.Print(prompt())
		if !sc.Scan() {
			fmt.Println()
			return
		}
		args := strings.Fields(strings.TrimSpace(sc.Text()))
		if len(args) == 0 {
			continue
		}
		cmd := strings.ToLower(args[0])
		switch cmd {
		case "exit", "quit", "q":
			return
		case "help", "?", "h":
			printConsoleHelp()
		case "banner":
			printBanner()
		case "clear", "cls":
			fmt.Print("\x1b[2J\x1b[H")
		case "show":
			showConfig(cfg)
		case "techs":
			printTechs()
		case "set":
			if len(args) < 3 {
				fmt.Println(paint(cYellow, "[!] uso: set <opção> <valor>"))
				continue
			}
			val := strings.Join(args[2:], " ")
			if msg := setOption(cfg, args[1], val); msg != "" {
				fmt.Println(paint(cRed, "[✗] "+msg))
			} else {
				fmt.Println(paint(cGreen, "[✓] "+strings.ToLower(args[1])+" = "+val))
			}
		case "scan", "s", "deep", "d":
			if len(args) < 2 {
				fmt.Println(paint(cYellow, "[!] uso: "+cmd+" <alvo>"))
				continue
			}
			c := *cfg
			c.Deep = cmd == "deep" || cmd == "d"
			runTargets(&c, args[1:])
		case "batch", "b":
			if len(args) < 2 {
				fmt.Println(paint(cYellow, "[!] uso: batch <arquivo>"))
				continue
			}
			list, err := readTargetFile(args[1])
			if err != nil || len(list) == 0 {
				fmt.Println(paint(cRed, "[✗] não foi possível ler alvos de "+args[1]))
				continue
			}
			c := *cfg
			runTargets(&c, list)
		default:
			if strings.Contains(cmd, ".") || strings.Contains(cmd, "://") {
				c := *cfg
				c.Deep = false
				runTargets(&c, args)
			} else {
				fmt.Println(paint(cRed, "[✗] comando desconhecido: "+cmd+" (digite help)"))
			}
		}
	}
}

func nextVal(args []string, i *int, flag string) (string, error) {
	if *i+1 >= len(args) {
		return "", fmt.Errorf("a opção %s precisa de um valor", flag)
	}
	*i++
	return args[*i], nil
}

func parseArgs(raw []string, cfg *Config) ([]string, error) {
	var args []string
	for _, a := range raw {
		if strings.HasPrefix(a, "--") && strings.Contains(a, "=") {
			kv := strings.SplitN(a, "=", 2)
			args = append(args, kv[0], kv[1])
		} else {
			args = append(args, a)
		}
	}
	var targets []string
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch a {
		case "-h", "--help":
			cfg.Help = true
		case "-V", "--version":
			cfg.Version = true
		case "-v", "--verbose":
			cfg.Verbose = true
		case "-a", "--deep":
			cfg.Deep = true
		case "-k", "--insecure":
			cfg.Insecure = true
		case "-i", "--console":
			cfg.Interactive = true
		case "--no-follow":
			cfg.Follow = false
		case "--no-geo":
			cfg.NoGeo = true
		case "--no-report":
			cfg.NoReport = true
		case "--no-color":
			cfg.NoColor = true
		case "--color":
			cfg.ForceColor = true
		case "--no-banner":
			cfg.NoBanner = true
		case "--json":
			cfg.JSON = true
			cfg.NoBanner = true
		case "--techs":
			cfg.ListTechs = true
		case "-t", "--threads":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			n, cerr := strconv.Atoi(v)
			if cerr != nil || n < 1 || n > 50 {
				return nil, fmt.Errorf("threads deve ser de 1 a 50")
			}
			cfg.Threads = n
		case "-T", "--timeout":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			n, cerr := strconv.Atoi(v)
			if cerr != nil || n < 1 || n > 120 {
				return nil, fmt.Errorf("timeout deve ser de 1 a 120 segundos")
			}
			cfg.Timeout = time.Duration(n) * time.Second
		case "-A", "--agent":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.Agent = v
		case "-H", "--header":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.Headers = append(cfg.Headers, v)
		case "-c", "--cookie":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.Cookie = v
		case "-x", "--proxy":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.Proxy = v
		case "-o", "--output":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.Output = v
		case "-l", "--list":
			v, err := nextVal(args, &i, a)
			if err != nil {
				return nil, err
			}
			cfg.List = v
		default:
			if strings.HasPrefix(a, "-") && len(a) > 1 {
				return nil, fmt.Errorf("opção desconhecida: %s", a)
			}
			targets = append(targets, a)
		}
	}
	return targets, nil
}

func main() {
	cfg := defaultConfig()
	targets, err := parseArgs(os.Args[1:], cfg)
	useColor = cfg.ForceColor || (!cfg.NoColor && os.Getenv("NO_COLOR") == "" && isTTY(os.Stdout))
	loadRules()
	if err != nil {
		fmt.Fprintln(os.Stderr, paint(cRed, "[✗] "+err.Error()))
		fmt.Fprintln(os.Stderr, paint(cGray, "    use moonscan -h para ver as opções"))
		os.Exit(2)
	}
	switch {
	case cfg.Version:
		fmt.Println(appName + " " + appVersion)
		return
	case cfg.Help:
		if !cfg.NoBanner {
			printBanner()
		}
		printHelp()
		return
	case cfg.ListTechs:
		printTechs()
		return
	}
	if cfg.List != "" {
		list, lerr := readTargetFile(cfg.List)
		if lerr != nil {
			fmt.Fprintln(os.Stderr, paint(cRed, "[✗] não foi possível abrir "+cfg.List+": "+lerr.Error()))
			os.Exit(2)
		}
		targets = append(targets, list...)
	}
	if len(targets) == 0 && !cfg.Interactive && !isTTY(os.Stdin) {
		targets = readTargets(os.Stdin)
	}
	if !cfg.NoBanner && !cfg.JSON {
		printBanner()
	}
	if len(targets) == 0 {
		console(cfg)
		return
	}
	failed := runTargets(cfg, targets)
	if failed == len(targets) {
		os.Exit(1)
	}
}
