function OnUpdate(doc, meta) {
    var request = {
        params: {
            'key1': '0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890',
            1: 2,
            'array': ['yes', 'this', 'is', 'an', 'array'],
            'key2': '0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890'
        }
    };

    curl('GET', requestUrl, request);
}

function OnDelete(meta) {
}
