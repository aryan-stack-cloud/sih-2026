        $("#Lsky").innerHTML = artSky();
        $("#Lfar").innerHTML = artFar();
        $("#Lbld").innerHTML = `<div id="bldBack" class="fill">${artBldBack()}</div><div id="facade3d">${artBuilding()}</div><div id="bldFront" class="fill">${artBldFront()}</div>`;
        $("#Lnear").innerHTML = artNear();
        $("#Lfg").innerHTML = artFg();
        $("#extBeam").innerHTML = `<defs>
            <linearGradient id="eb-g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f4f8ff" stop-opacity=".55"/><stop offset=".3" stop-color="#dbe6fb" stop-opacity=".2"/><stop offset="1" stop-color="#cbd9f5" stop-opacity=".06"/></linearGradient>
            <filter id="eb-soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5"/></filter>
            <pattern id="eb-haze" patternUnits="userSpaceOnUse" width="512" height="512"><image href="assets/img/haze.png" x="0" y="0" width="512" height="512"/></pattern>
            <clipPath id="eb-clip"><polygon id="eb-clipPoly" points="0,0 0,0 0,0"/></clipPath>
          </defs>
          <polygon id="eb-cone" points="0,0 0,0 0,0" fill="url(#eb-g)" filter="url(#eb-soft)" opacity="0" style="mix-blend-mode:screen"/>
          <g clip-path="url(#eb-clip)"><rect id="eb-hazeRect" x="-600" y="-600" width="3200" height="2400" fill="url(#eb-haze)" opacity="0" style="mix-blend-mode:screen"/></g>
          <g id="eb-seen" fill="none" stroke="#2fc596" stroke-width="4" opacity="0">
            <path id="eb-seenPath" d=""/>
          </g>
          <text id="eb-seenTxt" x="0" y="0" font-family="Archivo, sans-serif" font-weight="800" font-size="22" letter-spacing="3" fill="#2fc596" opacity="0">SEEN</text>`;
        $("#doorStage").innerHTML = artDoor();
        $("#reactStage").innerHTML = artReact();
        setA($("#rg-spot"), "transform", "translate(556 196) rotate(-34)");
        $("#roomStage").innerHTML = artRoom();
        $("#insertStage").innerHTML = artInsert();
        $("#otsSvg").innerHTML = `<defs>
            <radialGradient id="ot-lensg"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="#e3edff" stop-opacity=".6"/><stop offset="1" stop-color="#e3edff" stop-opacity="0"/></radialGradient>
            <linearGradient id="ot-streakg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#dfe9ff" stop-opacity="0"/><stop offset=".5" stop-color="#f6f9ff" stop-opacity=".9"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></linearGradient>
            <radialGradient id="ot-ghostg"><stop offset="0" stop-color="#bcd0f5" stop-opacity="0"/><stop offset=".7" stop-color="#bcd0f5" stop-opacity=".18"/><stop offset="1" stop-color="#bcd0f5" stop-opacity="0"/></radialGradient>
          </defs>
          <!-- the same desk-mounted spotlight as the wide shot, seen from behind the guard -->
          <rect x="884" y="880" width="30" height="240" fill="#141b2b"/><rect x="884" y="880" width="6" height="240" fill="#26304a"/>
          <path d="M846 902 L952 902 L940 872 L858 872 Z" fill="#1b2233"/>
          <g id="ot-lamp">
            <rect x="-86" y="-48" width="186" height="96" rx="16" fill="#27304a"/>
            <rect x="-86" y="-48" width="186" height="14" rx="7" fill="#46547c"/>
            <path d="M-70 -24 L84 -24 M-70 -8 L84 -8 M-70 8 L84 8 M-70 24 L84 24" stroke="#1d2540" stroke-width="3"/>
            <rect x="-72" y="-74" width="54" height="30" rx="12" fill="none" stroke="#27304a" stroke-width="10"/>
            <ellipse cx="100" cy="0" rx="14" ry="48" fill="#3a4666"/>
            <ellipse id="ot-lens" cx="104" cy="0" rx="9" ry="38" fill="#121a2a"/>
          </g>
          ${guardBack("ob")}
          <circle id="ot-lensglow" cx="0" cy="0" r="90" fill="url(#ot-lensg)" opacity="0" style="mix-blend-mode:screen"/>
          <ellipse id="ot-streak" cx="0" cy="0" rx="620" ry="3" fill="url(#ot-streakg)" opacity="0" style="mix-blend-mode:screen"/>
          <g id="ot-ghosts" opacity="0" style="mix-blend-mode:screen">
            <circle class="ghost" cx="0" cy="0" r="60" fill="url(#ot-ghostg)"/>
            <circle class="ghost" cx="0" cy="0" r="34" fill="url(#ot-ghostg)"/>
            <circle class="ghost" cx="0" cy="0" r="90" fill="url(#ot-ghostg)"/>
          </g>`;

