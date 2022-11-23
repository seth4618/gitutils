let diffdiv = null;

function hideme(event) {
    if (diffdiv != null) {
        diffdiv.style.display = 'none';
        diffdiv = null;
    }
}

function showDiff(event) {
    if (diffdiv != null)
        diffdiv.style.display = 'none';

    const target = event.target;
    const diff = `diff-${target.id}`;
    const elem = document.getElementById(diff);
    elem.style.display = 'block';
    diffdiv = elem;

    event.stopPropagation();
    event.preventDefault();
}

function initialize() {
    let branches = document.getElementsByClassName('branch');

    for (const element of branches)
        element.addEventListener('click', showDiff);

    document.getElementsByTagName('body')[0].addEventListener('click', hideme);
}
